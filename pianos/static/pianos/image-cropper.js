(function () {
    'use strict';

    const DEFAULTS = Object.freeze({
        aspectRatio: 16 / 10,
        previewWidth: 800,
        outputWidth: 1600,
        quality: 0.9,
        maxZoom: 4,
    });

    let activeSession = null;
    let sessionSequence = 0;

    function asPositiveNumber(value, fallback) {
        const number = Number(value);
        return Number.isFinite(number) && number > 0 ? number : fallback;
    }

    function asPositiveInteger(value, fallback) {
        return Math.max(1, Math.round(asPositiveNumber(value, fallback)));
    }

    function normaliseOptions(options) {
        const provided = options && typeof options === 'object' ? options : {};
        const aspectRatio = asPositiveNumber(provided.aspectRatio, DEFAULTS.aspectRatio);
        const previewWidth = asPositiveInteger(provided.previewWidth, DEFAULTS.previewWidth);
        const previewHeight = asPositiveInteger(
            provided.previewHeight,
            Math.round(previewWidth / aspectRatio),
        );
        const outputWidth = asPositiveInteger(provided.outputWidth, DEFAULTS.outputWidth);
        const outputHeight = asPositiveInteger(
            provided.outputHeight,
            Math.round(outputWidth / aspectRatio),
        );
        const quality = Math.min(1, Math.max(0.1, asPositiveNumber(provided.quality, DEFAULTS.quality)));
        const maxZoom = Math.max(1, asPositiveNumber(provided.maxZoom, DEFAULTS.maxZoom));

        const previewRatio = previewWidth / previewHeight;
        const outputRatio = outputWidth / outputHeight;
        if (Math.abs(previewRatio - outputRatio) > 0.01) {
            throw new Error('A proporção da prévia e da imagem final precisa ser a mesma.');
        }

        return {
            aspectRatio,
            previewWidth,
            previewHeight,
            outputWidth,
            outputHeight,
            quality,
            maxZoom,
            title: typeof provided.title === 'string' && provided.title.trim()
                ? provided.title.trim()
                : 'Ajustar foto',
            description: typeof provided.description === 'string' && provided.description.trim()
                ? provided.description.trim()
                : 'Arraste a foto e use o zoom para enquadrar o piano.',
            confirmLabel: typeof provided.confirmLabel === 'string' && provided.confirmLabel.trim()
                ? provided.confirmLabel.trim()
                : 'Usar esta foto',
            cancelLabel: typeof provided.cancelLabel === 'string' && provided.cancelLabel.trim()
                ? provided.cancelLabel.trim()
                : 'Cancelar',
            outputFileName: typeof provided.outputFileName === 'string' && provided.outputFileName.trim()
                ? provided.outputFileName.trim()
                : null,
        };
    }

    function createElement(tagName, className, text) {
        const element = document.createElement(tagName);
        if (className) element.className = className;
        if (typeof text === 'string') element.textContent = text;
        return element;
    }

    function outputFileName(file, configuredName) {
        if (configuredName) {
            return configuredName.toLowerCase().endsWith('.jpg') || configuredName.toLowerCase().endsWith('.jpeg')
                ? configuredName
                : `${configuredName}.jpg`;
        }

        const originalName = typeof file.name === 'string' ? file.name : 'foto';
        const baseName = originalName.replace(/\.[^/.]+$/, '').trim() || 'foto';
        return `${baseName}-16x10.jpg`;
    }

    function loadImage(objectUrl) {
        return new Promise((resolve, reject) => {
            const image = new Image();
            image.decoding = 'async';
            image.onload = () => {
                if (!image.naturalWidth || !image.naturalHeight) {
                    reject(new Error('A imagem selecionada não possui dimensões válidas.'));
                    return;
                }
                resolve(image);
            };
            image.onerror = () => reject(new Error('Não foi possível abrir esta imagem.'));
            // HTMLImageElement applies the orientation understood by the browser before canvas drawing.
            image.src = objectUrl;
        });
    }

    function focusableElements(container) {
        return Array.from(container.querySelectorAll(
            'button:not([disabled]), input:not([disabled]), [href], [tabindex]:not([tabindex="-1"])',
        )).filter((element) => !element.hidden && element.getClientRects().length > 0);
    }

    function crop(file, options) {
        if (activeSession) {
            return Promise.reject(new Error('Finalize o ajuste da foto atual antes de abrir outra.'));
        }
        if (!(file instanceof Blob) || !file.type || !file.type.startsWith('image/')) {
            return Promise.reject(new Error('Selecione um arquivo de imagem válido.'));
        }
        if (!document.body) {
            return Promise.reject(new Error('O editor de imagem ainda não está disponível.'));
        }

        let settings;
        try {
            settings = normaliseOptions(options);
        } catch (error) {
            return Promise.reject(error instanceof Error ? error : new Error(String(error)));
        }

        const token = ++sessionSequence;
        const previousFocus = document.activeElement instanceof HTMLElement
            ? document.activeElement
            : null;
        let objectUrl;

        try {
            objectUrl = URL.createObjectURL(file);
        } catch (error) {
            return Promise.reject(new Error('Não foi possível preparar a imagem selecionada.'));
        }

        activeSession = { token };

        return new Promise((resolve, reject) => {
            let mountedCleanup = null;
            let sessionCleaned = false;
            let objectUrlReleased = false;

            function releaseObjectUrl() {
                if (objectUrlReleased) return;
                objectUrlReleased = true;
                try {
                    URL.revokeObjectURL(objectUrl);
                } catch (error) {
                    // The browser may already have released the temporary URL.
                }
            }

            function restoreFocusImmediately() {
                if (!previousFocus || !previousFocus.isConnected) return;
                try {
                    previousFocus.focus({ preventScroll: true });
                } catch (error) {
                    try {
                        previousFocus.focus();
                    } catch (focusError) {
                        // The former element may no longer accept focus.
                    }
                }
            }

            function fallbackCleanup() {
                if (mountedCleanup) {
                    mountedCleanup();
                    return;
                }
                if (sessionCleaned) return;
                sessionCleaned = true;
                releaseObjectUrl();
                if (activeSession && activeSession.token === token) activeSession = null;
                restoreFocusImmediately();
            }

            loadImage(objectUrl).then((image) => {
                if (!activeSession || activeSession.token !== token) return;

                const overlay = createElement('div', 'pf-cropper-overlay');
                const dialog = createElement('section', 'pf-cropper-dialog');
                const header = createElement('header', 'pf-cropper-header');
                const headingWrap = createElement('div', 'pf-cropper-heading');
                const title = createElement('h2', 'pf-cropper-title', settings.title);
                const description = createElement('p', 'pf-cropper-description', settings.description);
                const closeButton = createElement('button', 'pf-cropper-close', '\u00d7');
                const main = createElement('div', 'pf-cropper-main');
                const stageFrame = createElement('div', 'pf-cropper-stage-frame');
                const stage = createElement('div', 'pf-cropper-stage');
                const canvas = createElement('canvas', 'pf-cropper-canvas');
                const grid = createElement('div', 'pf-cropper-grid');
                const hint = createElement(
                    'p',
                    'pf-cropper-hint',
                    'Arraste para mover. Use a roda do mouse ou o controle deslizante de Zoom abaixo. No celular, use o controle Zoom; o gesto de pinça não está disponível.',
                );
                const controls = createElement('div', 'pf-cropper-controls');
                const zoomLabel = createElement('label', 'pf-cropper-zoom-label', 'Zoom');
                const zoomInput = createElement('input', 'pf-cropper-zoom-input');
                const zoomValue = createElement('output', 'pf-cropper-zoom-value', '100%');
                const resetButton = createElement('button', 'pf-cropper-reset', 'Redefinir');
                const footer = createElement('footer', 'pf-cropper-footer');
                const cancelButton = createElement('button', 'pf-cropper-cancel', settings.cancelLabel);
                const confirmButton = createElement('button', 'pf-cropper-confirm', settings.confirmLabel);
                const status = createElement('p', 'pf-cropper-status');

                const titleId = `pf-cropper-title-${token}`;
                const descriptionId = `pf-cropper-description-${token}`;
                const zoomId = `pf-cropper-zoom-${token}`;
                title.id = titleId;
                description.id = descriptionId;
                zoomInput.id = zoomId;
                zoomLabel.htmlFor = zoomId;

                overlay.setAttribute('aria-hidden', 'false');
                dialog.setAttribute('role', 'dialog');
                dialog.setAttribute('aria-modal', 'true');
                dialog.setAttribute('aria-labelledby', titleId);
                dialog.setAttribute('aria-describedby', descriptionId);
                dialog.tabIndex = -1;
                closeButton.type = 'button';
                closeButton.setAttribute('aria-label', 'Fechar editor de foto');
                stage.tabIndex = 0;
                stage.setAttribute(
                    'aria-label',
                    'Área de enquadramento da foto. Arraste ou use as setas para mover a imagem.',
                );
                canvas.width = settings.previewWidth;
                canvas.height = settings.previewHeight;
                stage.style.aspectRatio = `${settings.previewWidth} / ${settings.previewHeight}`;
                zoomInput.type = 'range';
                zoomInput.min = '1';
                zoomInput.max = String(settings.maxZoom);
                zoomInput.step = '0.01';
                zoomInput.value = '1';
                zoomInput.setAttribute('aria-label', 'Nível de zoom da foto');
                zoomValue.htmlFor = zoomId;
                resetButton.type = 'button';
                cancelButton.type = 'button';
                confirmButton.type = 'button';
                status.setAttribute('role', 'status');
                status.setAttribute('aria-live', 'polite');

                headingWrap.append(title, description);
                header.append(headingWrap, closeButton);
                stage.append(canvas, grid);
                stageFrame.append(stage);
                controls.append(zoomLabel, zoomInput, zoomValue, resetButton);
                main.append(stageFrame, hint, controls, status);
                footer.append(cancelButton, confirmButton);
                dialog.append(header, main, footer);
                overlay.append(dialog);

                const context = canvas.getContext('2d', { alpha: false });
                if (!context) {
                    throw new Error('O navegador não conseguiu iniciar o editor de imagem.');
                }

                let finished = false;
                let scrollLockApplied = false;
                const inertRecords = [];
                const scrollPosition = {
                    x: window.scrollX || window.pageXOffset || 0,
                    y: window.scrollY || window.pageYOffset || 0,
                };
                const bodyStyle = {
                    overflow: document.body.style.overflow,
                    overscrollBehavior: document.body.style.overscrollBehavior,
                    paddingRight: document.body.style.paddingRight,
                    position: document.body.style.position,
                    top: document.body.style.top,
                    left: document.body.style.left,
                    width: document.body.style.width,
                };
                const htmlStyle = {
                    overflow: document.documentElement.style.overflow,
                    overscrollBehavior: document.documentElement.style.overscrollBehavior,
                    scrollBehavior: document.documentElement.style.scrollBehavior,
                };
                const scrollbarWidth = Math.max(0, window.innerWidth - document.documentElement.clientWidth);
                const computedBodyPadding = Number.parseFloat(window.getComputedStyle(document.body).paddingRight) || 0;

                function restoreInertSiblings() {
                    inertRecords.forEach((record) => {
                        try {
                            record.element.inert = record.propertyValue;
                            if (record.hadAttribute) {
                                record.element.setAttribute('inert', record.attributeValue || '');
                            } else {
                                record.element.removeAttribute('inert');
                            }
                        } catch (error) {
                            // Continue restoring the remaining page siblings.
                        }
                    });
                    inertRecords.length = 0;
                }

                function restoreScrollLock() {
                    if (!scrollLockApplied) return;
                    scrollLockApplied = false;

                    try {
                        document.body.style.overflow = bodyStyle.overflow;
                        document.body.style.overscrollBehavior = bodyStyle.overscrollBehavior;
                        document.body.style.paddingRight = bodyStyle.paddingRight;
                        document.body.style.position = bodyStyle.position;
                        document.body.style.top = bodyStyle.top;
                        document.body.style.left = bodyStyle.left;
                        document.body.style.width = bodyStyle.width;
                        document.documentElement.style.overflow = htmlStyle.overflow;
                        document.documentElement.style.overscrollBehavior = htmlStyle.overscrollBehavior;

                        // Keep restoration immediate even when the site enables smooth scrolling.
                        document.documentElement.style.scrollBehavior = 'auto';
                        window.scrollTo(scrollPosition.x, scrollPosition.y);
                    } finally {
                        document.documentElement.style.scrollBehavior = htmlStyle.scrollBehavior;
                    }
                }

                function cleanup() {
                    if (sessionCleaned) return;
                    sessionCleaned = true;

                    try {
                        document.removeEventListener('keydown', onDocumentKeyDown, true);
                        stage.removeEventListener('pointerdown', onPointerDown);
                        stage.removeEventListener('pointermove', onPointerMove);
                        stage.removeEventListener('pointerup', endPointer);
                        stage.removeEventListener('pointercancel', endPointer);
                        stage.removeEventListener('wheel', onWheel);
                        stage.removeEventListener('keydown', onStageKeyDown);
                    } catch (error) {
                        // Continue restoring the page even if a browser rejects listener cleanup.
                    }

                    try {
                        overlay.remove();
                    } catch (error) {
                        try {
                            if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
                        } catch (removeError) {
                            // Continue restoring the rest of the page.
                        }
                    }

                    try {
                        restoreInertSiblings();
                    } catch (error) {
                        // Continue with scroll and focus restoration.
                    }
                    try {
                        restoreScrollLock();
                    } catch (error) {
                        // Continue releasing the image and active session.
                    }

                    try {
                        image.removeAttribute('src');
                    } catch (error) {
                        // Image cleanup is best effort.
                    }
                    releaseObjectUrl();
                    if (activeSession && activeSession.token === token) activeSession = null;

                    try {
                        window.requestAnimationFrame(() => {
                            // A new cropper may have opened before this frame.
                            if (activeSession) return;
                            restoreFocusImmediately();
                            try {
                                document.documentElement.style.scrollBehavior = 'auto';
                                window.scrollTo(scrollPosition.x, scrollPosition.y);
                            } finally {
                                document.documentElement.style.scrollBehavior = htmlStyle.scrollBehavior;
                            }
                        });
                    } catch (error) {
                        restoreFocusImmediately();
                    }
                }

                function finish(result, error) {
                    if (finished) return;
                    finished = true;
                    cleanup();
                    if (error) reject(error);
                    else resolve(result);
                }

                // Register cleanup before any operation that mutates the page.
                mountedCleanup = cleanup;
                scrollLockApplied = true;
                if (scrollbarWidth) {
                    document.body.style.paddingRight = `${computedBodyPadding + scrollbarWidth}px`;
                }
                document.body.style.overflow = 'hidden';
                document.body.style.overscrollBehavior = 'none';
                document.body.style.position = 'fixed';
                document.body.style.top = `-${scrollPosition.y}px`;
                document.body.style.left = `-${scrollPosition.x}px`;
                document.body.style.width = '100%';
                document.documentElement.style.overflow = 'hidden';
                document.documentElement.style.overscrollBehavior = 'none';
                document.documentElement.style.scrollBehavior = 'auto';
                document.body.appendChild(overlay);

                if ('inert' in HTMLElement.prototype) {
                    Array.from(document.body.children).forEach((element) => {
                        if (element === overlay || !('inert' in element)) return;
                        const record = {
                            element,
                            propertyValue: element.inert,
                            hadAttribute: element.hasAttribute('inert'),
                            attributeValue: element.getAttribute('inert'),
                        };
                        inertRecords.push(record);
                        element.inert = true;
                    });
                }

                const state = {
                    minScale: Math.max(
                        canvas.width / image.naturalWidth,
                        canvas.height / image.naturalHeight,
                    ),
                    scale: 1,
                    offsetX: 0,
                    offsetY: 0,
                    pointerId: null,
                    lastClientX: 0,
                    lastClientY: 0,
                    busy: false,
                };
                state.scale = state.minScale;

                function clampOffsets() {
                    const imageWidth = image.naturalWidth * state.scale;
                    const imageHeight = image.naturalHeight * state.scale;
                    const minX = canvas.width - imageWidth;
                    const minY = canvas.height - imageHeight;
                    state.offsetX = imageWidth <= canvas.width
                        ? (canvas.width - imageWidth) / 2
                        : Math.min(0, Math.max(minX, state.offsetX));
                    state.offsetY = imageHeight <= canvas.height
                        ? (canvas.height - imageHeight) / 2
                        : Math.min(0, Math.max(minY, state.offsetY));
                }

                function drawPreview() {
                    clampOffsets();
                    context.save();
                    context.fillStyle = '#ffffff';
                    context.fillRect(0, 0, canvas.width, canvas.height);
                    context.imageSmoothingEnabled = true;
                    context.imageSmoothingQuality = 'high';
                    context.drawImage(
                        image,
                        state.offsetX,
                        state.offsetY,
                        image.naturalWidth * state.scale,
                        image.naturalHeight * state.scale,
                    );
                    context.restore();
                }

                function zoomFactor() {
                    return state.scale / state.minScale;
                }

                function updateZoomControls() {
                    const factor = zoomFactor();
                    zoomInput.value = String(factor);
                    zoomValue.value = `${Math.round(factor * 100)}%`;
                    zoomValue.textContent = zoomValue.value;
                }

                function setZoom(factor, anchorX, anchorY) {
                    const boundedFactor = Math.min(settings.maxZoom, Math.max(1, factor));
                    const targetX = Number.isFinite(anchorX) ? anchorX : canvas.width / 2;
                    const targetY = Number.isFinite(anchorY) ? anchorY : canvas.height / 2;
                    const sourceX = (targetX - state.offsetX) / state.scale;
                    const sourceY = (targetY - state.offsetY) / state.scale;
                    state.scale = state.minScale * boundedFactor;
                    state.offsetX = targetX - sourceX * state.scale;
                    state.offsetY = targetY - sourceY * state.scale;
                    drawPreview();
                    updateZoomControls();
                }

                function resetCrop() {
                    state.scale = state.minScale;
                    state.offsetX = (canvas.width - image.naturalWidth * state.scale) / 2;
                    state.offsetY = (canvas.height - image.naturalHeight * state.scale) / 2;
                    drawPreview();
                    updateZoomControls();
                }

                function moveImage(deltaX, deltaY) {
                    state.offsetX += deltaX;
                    state.offsetY += deltaY;
                    drawPreview();
                }

                function setBusy(isBusy) {
                    state.busy = isBusy;
                    dialog.setAttribute('aria-busy', isBusy ? 'true' : 'false');
                    closeButton.disabled = isBusy;
                    cancelButton.disabled = isBusy;
                    confirmButton.disabled = isBusy;
                    resetButton.disabled = isBusy;
                    zoomInput.disabled = isBusy;
                    confirmButton.textContent = isBusy ? 'Processando...' : settings.confirmLabel;
                    status.textContent = isBusy ? 'Preparando a foto ajustada.' : '';
                }

                function onPointerDown(event) {
                    if (state.busy || state.pointerId !== null) return;
                    if (event.pointerType === 'mouse' && event.button !== 0) return;
                    event.preventDefault();
                    state.pointerId = event.pointerId;
                    state.lastClientX = event.clientX;
                    state.lastClientY = event.clientY;
                    stage.classList.add('pf-cropper-stage-dragging');
                    if (stage.setPointerCapture) stage.setPointerCapture(event.pointerId);
                }

                function onPointerMove(event) {
                    if (state.busy || event.pointerId !== state.pointerId) return;
                    event.preventDefault();
                    const rect = stage.getBoundingClientRect();
                    if (!rect.width || !rect.height) return;
                    const deltaX = (event.clientX - state.lastClientX) * (canvas.width / rect.width);
                    const deltaY = (event.clientY - state.lastClientY) * (canvas.height / rect.height);
                    state.lastClientX = event.clientX;
                    state.lastClientY = event.clientY;
                    moveImage(deltaX, deltaY);
                }

                function endPointer(event) {
                    if (event.pointerId !== state.pointerId) return;
                    if (stage.releasePointerCapture && stage.hasPointerCapture(event.pointerId)) {
                        stage.releasePointerCapture(event.pointerId);
                    }
                    state.pointerId = null;
                    stage.classList.remove('pf-cropper-stage-dragging');
                }

                function onWheel(event) {
                    if (state.busy) return;
                    event.preventDefault();
                    const rect = stage.getBoundingClientRect();
                    if (!rect.width || !rect.height) return;
                    const anchorX = (event.clientX - rect.left) * (canvas.width / rect.width);
                    const anchorY = (event.clientY - rect.top) * (canvas.height / rect.height);
                    const nextFactor = zoomFactor() * Math.exp(-event.deltaY * 0.0015);
                    setZoom(nextFactor, anchorX, anchorY);
                }

                function onStageKeyDown(event) {
                    if (state.busy) return;
                    const step = event.shiftKey ? 40 : 12;
                    if (event.key === 'ArrowLeft') {
                        event.preventDefault();
                        moveImage(-step, 0);
                    } else if (event.key === 'ArrowRight') {
                        event.preventDefault();
                        moveImage(step, 0);
                    } else if (event.key === 'ArrowUp') {
                        event.preventDefault();
                        moveImage(0, -step);
                    } else if (event.key === 'ArrowDown') {
                        event.preventDefault();
                        moveImage(0, step);
                    } else if (event.key === '+' || event.key === '=') {
                        event.preventDefault();
                        setZoom(zoomFactor() + 0.1);
                    } else if (event.key === '-') {
                        event.preventDefault();
                        setZoom(zoomFactor() - 0.1);
                    }
                }

                function onDocumentKeyDown(event) {
                    if (event.key === 'Escape') {
                        if (!state.busy) {
                            event.preventDefault();
                            finish(null);
                        }
                        return;
                    }
                    if (event.key !== 'Tab') return;

                    const focusable = focusableElements(dialog);
                    if (!focusable.length) {
                        event.preventDefault();
                        dialog.focus();
                        return;
                    }
                    const first = focusable[0];
                    const last = focusable[focusable.length - 1];
                    if (!dialog.contains(document.activeElement)) {
                        event.preventDefault();
                        (event.shiftKey ? last : first).focus();
                    } else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog)) {
                        event.preventDefault();
                        last.focus();
                    } else if (!event.shiftKey && document.activeElement === last) {
                        event.preventDefault();
                        first.focus();
                    }
                }

                function createOutputFile() {
                    return new Promise((resolveOutput, rejectOutput) => {
                        try {
                            const outputCanvas = document.createElement('canvas');
                            outputCanvas.width = settings.outputWidth;
                            outputCanvas.height = settings.outputHeight;
                            const outputContext = outputCanvas.getContext('2d', { alpha: false });
                            if (!outputContext) {
                                throw new Error('O navegador não conseguiu gerar a foto ajustada.');
                            }

                            const sourceWidth = canvas.width / state.scale;
                            const sourceHeight = canvas.height / state.scale;
                            const sourceX = Math.max(
                                0,
                                Math.min(image.naturalWidth - sourceWidth, -state.offsetX / state.scale),
                            );
                            const sourceY = Math.max(
                                0,
                                Math.min(image.naturalHeight - sourceHeight, -state.offsetY / state.scale),
                            );

                            outputContext.fillStyle = '#ffffff';
                            outputContext.fillRect(0, 0, outputCanvas.width, outputCanvas.height);
                            outputContext.imageSmoothingEnabled = true;
                            outputContext.imageSmoothingQuality = 'high';
                            outputContext.drawImage(
                                image,
                                sourceX,
                                sourceY,
                                sourceWidth,
                                sourceHeight,
                                0,
                                0,
                                outputCanvas.width,
                                outputCanvas.height,
                            );

                            outputCanvas.toBlob((blob) => {
                                if (!blob) {
                                    rejectOutput(new Error('Não foi possível salvar a foto ajustada.'));
                                    return;
                                }
                                try {
                                    resolveOutput(new File(
                                        [blob],
                                        outputFileName(file, settings.outputFileName),
                                        { type: 'image/jpeg', lastModified: Date.now() },
                                    ));
                                } catch (error) {
                                    rejectOutput(new Error('Não foi possível criar o arquivo da foto ajustada.'));
                                }
                            }, 'image/jpeg', settings.quality);
                        } catch (error) {
                            rejectOutput(error instanceof Error ? error : new Error(String(error)));
                        }
                    });
                }

                closeButton.addEventListener('click', () => finish(null));
                cancelButton.addEventListener('click', () => finish(null));
                resetButton.addEventListener('click', resetCrop);
                confirmButton.addEventListener('click', () => {
                    if (state.busy) return;
                    setBusy(true);
                    createOutputFile()
                        .then((result) => finish(result))
                        .catch((error) => finish(null, error));
                });
                zoomInput.addEventListener('input', () => setZoom(Number(zoomInput.value)));
                stage.addEventListener('pointerdown', onPointerDown);
                stage.addEventListener('pointermove', onPointerMove);
                stage.addEventListener('pointerup', endPointer);
                stage.addEventListener('pointercancel', endPointer);
                stage.addEventListener('wheel', onWheel, { passive: false });
                stage.addEventListener('keydown', onStageKeyDown);
                overlay.addEventListener('pointerdown', (event) => {
                    if (event.target === overlay && !state.busy) finish(null);
                });
                document.addEventListener('keydown', onDocumentKeyDown, true);

                resetCrop();
                window.requestAnimationFrame(() => closeButton.focus());
            }).catch((error) => {
                fallbackCleanup();
                reject(error instanceof Error ? error : new Error(String(error)));
            });
        });
    }

    window.PianoImageCropper = Object.freeze({ crop });
}());
