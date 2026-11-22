(function () {
    'use strict';

    const INPUT_SELECTOR = 'input[type="file"][data-piano-image-cropper]';
    const ASPECT_RATIO = 16 / 10;
    const OUTPUT_WIDTH = 1600;
    const OUTPUT_HEIGHT = 1000;
    const MAX_FILE_SIZE = 10 * 1024 * 1024;

    function fileWrapper(input) {
        return input.closest('.border') || input;
    }

    function showFileName(input, name) {
        const label = fileWrapper(input).querySelector('input[type="text"][disabled]');
        if (label) label.value = name;
    }

    function createStatus(input) {
        const status = document.createElement('div');
        status.className = 'piano-image-crop-status';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        status.setAttribute('aria-atomic', 'true');
        status.style.marginTop = '8px';
        // No Unfold o input real fica escondido dentro de uma moldura com borda;
        // a mensagem precisa aparecer depois da moldura para ficar visível.
        fileWrapper(input).insertAdjacentElement('afterend', status);
        input.setAttribute('aria-describedby', [
            input.getAttribute('aria-describedby'),
            status.id || (status.id = `${input.id || 'piano-image'}-crop-status`),
        ].filter(Boolean).join(' '));
        return status;
    }

    function getSubmitControls(form) {
        return Array.from(form.querySelectorAll(
            'button[type="submit"], input[type="submit"]'
        ));
    }

    function replaceSelectedFile(input, croppedResult, originalFile) {
        const croppedBlob = croppedResult && (
            croppedResult.file || croppedResult.blob || croppedResult
        );

        if (!(croppedBlob instanceof Blob)) {
            throw new Error('O recortador não retornou uma imagem válida.');
        }

        const sourceName = originalFile.name.replace(/\.[^.]+$/, '') || 'piano';
        const croppedFile = croppedBlob instanceof File
            ? croppedBlob
            : new File(
                [croppedBlob],
                `${sourceName}-16x10.jpg`,
                { type: croppedBlob.type || 'image/jpeg', lastModified: Date.now() }
            );

        if (typeof DataTransfer !== 'function') {
            throw new Error('Este navegador não permite preparar a imagem recortada.');
        }

        const transfer = new DataTransfer();
        transfer.items.add(croppedFile);
        input.files = transfer.files;
    }

    function bindCropper(input) {
        const form = input.closest('form');
        if (!form || input.dataset.pianoImageCropperBound === 'true') return;

        input.dataset.pianoImageCropperBound = 'true';
        const status = createStatus(input);
        let processing = false;
        let submitStates = new Map();

        function setStatus(message, isError) {
            status.textContent = message;
            status.classList.toggle('errornote', Boolean(isError));
        }

        function setProcessing(value) {
            processing = value;
            input.setAttribute('aria-busy', value ? 'true' : 'false');

            const controls = getSubmitControls(form);
            if (value) {
                submitStates = new Map(controls.map(control => [control, control.disabled]));
                controls.forEach(control => { control.disabled = true; });
            } else {
                controls.forEach(control => {
                    control.disabled = submitStates.get(control) || false;
                });
                submitStates.clear();
            }
        }

        input.addEventListener('change', async function () {
            const originalFile = input.files && input.files[0];
            if (!originalFile || processing) return;

            if (originalFile.size > MAX_FILE_SIZE) {
                input.value = '';
                setStatus('A imagem original deve ter no máximo 10 MB.', true);
                return;
            }

            setProcessing(true);
            setStatus('Ajuste a foto na moldura 16:10 antes de continuar.', false);

            // Remove o original do formulário imediatamente. Somente a versão
            // confirmada no recortador poderá ser enviada ao servidor.
            input.value = '';

            try {
                const cropper = window.PianoImageCropper;
                if (!cropper || typeof cropper.crop !== 'function') {
                    throw new Error('O editor de imagem não foi carregado.');
                }

                const croppedResult = await cropper.crop(originalFile, {
                    aspectRatio: ASPECT_RATIO,
                    outputWidth: OUTPUT_WIDTH,
                    outputHeight: OUTPUT_HEIGHT,
                });

                if (!croppedResult) {
                    setStatus('Ajuste cancelado. Escolha uma foto para tentar novamente.', false);
                    return;
                }

                replaceSelectedFile(input, croppedResult, originalFile);
                showFileName(input, input.files[0].name);
                setStatus('Foto ajustada em 16:10 e pronta para ser salva.', false);
                input.dispatchEvent(new CustomEvent('piano:image-cropped', {
                    bubbles: true,
                    detail: { file: input.files[0] },
                }));
            } catch (error) {
                input.value = '';
                const cancelled = error && error.name === 'AbortError';
                setStatus(
                    cancelled
                        ? 'Ajuste cancelado. Escolha uma foto para tentar novamente.'
                        : `Não foi possível ajustar a foto: ${error.message || 'erro inesperado'}`,
                    !cancelled
                );
                if (!cancelled) console.error('Erro ao recortar imagem no Django Admin:', error);
            } finally {
                setProcessing(false);
            }
        });

        form.addEventListener('submit', function (event) {
            if (!processing) return;
            event.preventDefault();
            event.stopImmediatePropagation();
            setStatus('Conclua ou cancele o ajuste da foto antes de salvar.', true);
        }, true);
    }

    function init() {
        document.querySelectorAll(INPUT_SELECTOR).forEach(bindCropper);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
}());
