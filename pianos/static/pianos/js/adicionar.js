// Formulário público de cadastro: tipo de piano, recorte 16:10 e upload direto ao Cloudinary.
(function () {
    'use strict';

    // ── Tipo ──
    const tipoFinal = document.getElementById('tipoFinal');
    const subWrap = document.getElementById('subAcustico');

    function updateTipo() {
        const categoria = document.querySelector('input[name="tipo_cat"]:checked')?.value;
        const acustico = categoria === 'acustico';
        subWrap.classList.toggle('hidden', !acustico);
        tipoFinal.value = acustico
            ? (document.querySelector('input[name="tipo_sub"]:checked')?.value || 'armario')
            : (categoria || 'digital');
    }
    document.querySelectorAll('input[name="tipo_cat"], input[name="tipo_sub"]')
        .forEach(radio => radio.addEventListener('change', updateTipo));
    updateTipo();

    // ── Upload direto ao Cloudinary ──
    const CLOUD = document.getElementById('cloudinary_cloud_name').value;
    const PRESET = document.getElementById('cloudinary_preset').value;
    const MAX_FILE_SIZE = 10 * 1024 * 1024;
    const urlInputs = ['foto_url_1', 'foto_url_2', 'foto_url_3'].map(id => document.getElementById(id));
    const fileInputs = ['fotoInput', 'fotoInput2', 'fotoInput3'].map(id => document.getElementById(id));
    const preview = document.getElementById('fotosPreview');
    const btnAdd = document.getElementById('btnAddFoto');
    const dropzone = document.getElementById('dropzone');
    const btnSubmit = document.getElementById('btnSubmit');
    const uploadError = document.getElementById('uploadError');

    let cropPending = 0;
    let cropQueue = Promise.resolve();
    // Cada posição: { localUrl, uploading, error, token, controller } ou null.
    const slots = [null, null, null];

    function showUploadError(message = '') {
        uploadError.textContent = message;
        uploadError.classList.toggle('hidden', !message);
    }

    function overlay(text) {
        const el = document.createElement('div');
        el.className = 'absolute inset-0 grid place-items-center bg-black/55 text-[0.6rem] tracking-wide text-white';
        el.textContent = text;
        return el;
    }

    function renderPreview() {
        preview.replaceChildren();
        const usados = slots.filter(Boolean).length;
        const pendentes = slots.filter(s => s && s.uploading).length;
        const falhas = slots.filter(s => s && s.error).length;

        slots.forEach((slot, i) => {
            if (!slot) return;
            const thumb = document.createElement('div');
            thumb.className = 'relative aspect-[16/10] w-[clamp(96px,28vw,140px)] overflow-hidden rounded border border-line';

            const img = document.createElement('img');
            img.src = slot.localUrl;
            img.alt = `Foto ${i + 1}`;
            img.className = 'size-full object-cover';

            const num = document.createElement('span');
            num.className = 'absolute bottom-1 left-1.5 text-[0.55rem] font-semibold text-gold';
            num.textContent = `0${i + 1}`;

            const remove = document.createElement('button');
            remove.type = 'button';
            remove.className = 'absolute top-1 right-1 grid size-5 place-items-center rounded-full bg-black/75 text-xs text-white hover:bg-danger';
            remove.textContent = '×';
            remove.setAttribute('aria-label', `Remover foto ${i + 1}`);
            remove.addEventListener('click', () => {
                if (slot.controller) slot.controller.abort();
                URL.revokeObjectURL(slot.localUrl);
                slots[i] = null;
                urlInputs[i].value = '';
                if (!slots.some(s => s && s.error)) showUploadError();
                renderPreview();
            });

            thumb.append(img, num, remove);
            if (slot.uploading) thumb.appendChild(overlay('enviando…'));
            else if (slot.error) thumb.appendChild(overlay('falhou'));
            preview.appendChild(thumb);
        });

        btnSubmit.disabled = cropPending > 0 || pendentes > 0 || falhas > 0;
        if (cropPending > 0) btnSubmit.textContent = 'Ajustando foto...';
        else if (pendentes > 0) btnSubmit.textContent = `Aguarde... (${pendentes} foto${pendentes > 1 ? 's' : ''})`;
        else if (falhas > 0) btnSubmit.textContent = 'Remova a foto com erro';
        else btnSubmit.textContent = 'Enviar para aprovação';

        dropzone.classList.toggle('hidden', usados > 0);
        btnAdd.classList.toggle('hidden', usados === 0 || usados >= 3);
        btnAdd.classList.toggle('flex', usados > 0 && usados < 3);
    }

    async function uploadFoto(file, idx) {
        const token = slots[idx].token;
        const controller = new AbortController();
        const timeoutId = window.setTimeout(() => controller.abort(), 60000);
        const body = new FormData();
        body.append('file', file);
        body.append('upload_preset', PRESET);
        slots[idx].uploading = true;
        slots[idx].controller = controller;
        renderPreview();
        try {
            if (!CLOUD || !PRESET) throw new Error('Configuração de upload indisponível.');
            const res = await fetch(`https://api.cloudinary.com/v1_1/${CLOUD}/image/upload`, {
                method: 'POST',
                body,
                signal: controller.signal,
            });
            const data = await res.json();
            if (!res.ok || !data.secure_url) {
                throw new Error(data.error?.message || 'O Cloudinary recusou a imagem.');
            }
            if (!slots[idx] || slots[idx].token !== token) return;
            Object.assign(slots[idx], { uploading: false, error: false, controller: null });
            urlInputs[idx].value = data.secure_url;
        } catch (error) {
            if (!slots[idx] || slots[idx].token !== token) return;
            Object.assign(slots[idx], { uploading: false, error: true, controller: null });
            urlInputs[idx].value = '';
            const reason = error.name === 'AbortError' ? 'o envio demorou mais de 60 segundos' : error.message;
            showUploadError(`Não foi possível enviar a foto: ${reason}. Remova-a e tente novamente.`);
            console.error('Erro no upload:', error);
        } finally {
            window.clearTimeout(timeoutId);
        }
        renderPreview();
    }

    function validateImageFile(file) {
        if (!file || !file.type.startsWith('image/')) {
            showUploadError('Escolha um arquivo de imagem válido.');
            return false;
        }
        if (file.size > MAX_FILE_SIZE) {
            showUploadError('Cada foto deve ter no máximo 10 MB.');
            return false;
        }
        return true;
    }

    async function addFile(file) {
        if (!validateImageFile(file)) return;
        if (!window.PianoImageCropper) {
            showUploadError('O ajustador de imagem não foi carregado. Atualize a página e tente novamente.');
            return;
        }
        if (!slots.includes(null)) return;

        cropPending += 1;
        renderPreview();
        let croppedFile;
        try {
            croppedFile = await window.PianoImageCropper.crop(file, {
                aspectRatio: 16 / 10,
                outputWidth: 1600,
                outputHeight: 1000,
                quality: 0.9,
            });
        } catch (error) {
            showUploadError(`Não foi possível ajustar a foto: ${error.message}`);
            console.error('Erro no recorte:', error);
            return;
        } finally {
            cropPending -= 1;
            renderPreview();
        }

        if (!croppedFile || !validateImageFile(croppedFile)) return;
        const idx = slots.indexOf(null);
        if (idx === -1) return;
        if (!slots.some(s => s && s.error)) showUploadError();
        slots[idx] = {
            localUrl: URL.createObjectURL(croppedFile),
            uploading: false,
            error: false,
            token: `${Date.now()}-${Math.random()}`,
            controller: null,
        };
        renderPreview();
        uploadFoto(croppedFile, idx);
    }

    function enqueueFile(file) {
        cropQueue = cropQueue
            .then(() => addFile(file))
            .catch(error => {
                showUploadError(`Não foi possível processar a foto: ${error.message}`);
                console.error('Erro ao processar fila de imagens:', error);
            });
        return cropQueue;
    }

    function handleFileInput() {
        const file = this.files[0];
        this.value = '';
        if (file) enqueueFile(file);
    }
    fileInputs.forEach(input => input.addEventListener('change', handleFileInput));

    btnAdd.addEventListener('click', () => {
        const idx = slots.indexOf(null);
        if (idx >= 0) fileInputs[idx].click();
    });

    dropzone.addEventListener('dragover', event => { event.preventDefault(); dropzone.classList.add('drag-over'); });
    dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
    dropzone.addEventListener('drop', event => {
        event.preventDefault();
        dropzone.classList.remove('drag-over');
        [...event.dataTransfer.files]
            .filter(file => file.type.startsWith('image/'))
            .slice(0, 3)
            .forEach(enqueueFile);
    });

    // Barra de progresso ao enviar.
    document.getElementById('mainForm').addEventListener('submit', event => {
        if (cropPending > 0 || slots.some(s => s && (s.uploading || s.error))) {
            event.preventDefault();
            showUploadError('Conclua o ajuste das fotos, aguarde os uploads ou remova a foto que apresentou erro.');
            return;
        }
        const bar = document.getElementById('loading-bar');
        bar.classList.remove('hidden');
        let width = 0;
        window.setInterval(() => {
            width = Math.min(85, width + Math.random() * 15);
            bar.style.width = `${width}%`;
        }, 300);
    });

    // Evita que o navegador preencha os campos com dados salvos de outros sites.
    document.querySelectorAll('#mainForm input:not([type=file]):not([type=radio]):not([type=checkbox]):not([type=hidden]), #mainForm textarea')
        .forEach(el => {
            el.setAttribute('autocomplete', 'new-password');
            el.setAttribute('readonly', true);
            el.addEventListener('focus', () => el.removeAttribute('readonly'));
        });

    renderPreview();
}());
