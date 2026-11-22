// Curtir, avaliar e compartilhar na página de detalhe do piano.
(function () {
    'use strict';

    function csrfToken() {
        const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
        if (match) return decodeURIComponent(match[1]);
        const input = document.querySelector('input[name="csrfmiddlewaretoken"]');
        return input ? input.value : '';
    }

    async function post(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken(),
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: new URLSearchParams(data),
            credentials: 'same-origin',
        });
        let body = {};
        try { body = await response.json(); } catch (error) { /* resposta sem JSON (ex.: 429) */ }
        if (!response.ok) {
            const message = response.status === 429
                ? 'Muitas tentativas. Aguarde um pouco.'
                : (body.erro || 'Não foi possível concluir. Tente de novo.');
            throw new Error(message);
        }
        return body;
    }

    // ── Curtir ──
    const likeButton = document.querySelector('[data-like-url]');
    if (likeButton) {
        const count = likeButton.querySelector('[data-like-count]');
        likeButton.addEventListener('click', async () => {
            likeButton.disabled = true;
            try {
                const data = await post(likeButton.dataset.likeUrl, { acao: 'like' });
                count.textContent = data.likes;
                likeButton.setAttribute('aria-pressed', data.voto_atual === 'like' ? 'true' : 'false');
                likeButton.removeAttribute('title');
            } catch (error) {
                likeButton.title = error.message;
            } finally {
                likeButton.disabled = false;
            }
        });
    }

    // ── Estrelas ──
    const rating = document.querySelector('[data-rating-url]');
    if (rating) {
        const stars = [...rating.querySelectorAll('[data-star]')];
        const status = rating.querySelector('[data-rating-status]');
        const paint = value => stars.forEach((star, i) => { star.dataset.on = String(i < value); });
        const lock = value => {
            stars.forEach((star, i) => {
                star.disabled = true;
                star.setAttribute('aria-checked', String(i + 1 === value));
            });
            paint(value);
            status.textContent = `Você avaliou ${value}★`;
            status.classList.replace('text-muted', 'text-gold');
        };

        const mine = Number(rating.dataset.minhaAvaliacao || 0);
        if (mine) {
            lock(mine);
        } else {
            const initial = stars.map(star => star.dataset.on);
            const restore = () => stars.forEach((star, i) => { star.dataset.on = initial[i]; });
            stars.forEach(star => {
                const value = Number(star.dataset.star);
                star.addEventListener('mouseenter', () => paint(value));
                star.addEventListener('focus', () => paint(value));
                star.addEventListener('mouseleave', restore);
                star.addEventListener('blur', restore);
                star.addEventListener('click', async () => {
                    stars.forEach(s => { s.disabled = true; });
                    try {
                        const data = await post(rating.dataset.ratingUrl, { estrelas: value });
                        rating.querySelector('[data-rating-avg]').textContent = Number(data.estrelas).toFixed(1);
                        rating.querySelector('[data-rating-total]').textContent = `(${data.total_avaliacoes})`;
                        lock(value);
                    } catch (error) {
                        status.textContent = error.message;
                        stars.forEach(s => { s.disabled = false; });
                    }
                });
            });
        }
    }

    // ── Compartilhar ──
    const share = document.querySelector('[data-share]');
    if (share) {
        const label = share.querySelector('[data-share-label]');
        share.addEventListener('click', async () => {
            const data = {
                title: share.dataset.shareTitle,
                text: 'Achei esse piano público no Piano Finder!',
                url: window.location.href,
            };
            if (navigator.share) {
                try { await navigator.share(data); } catch (error) { /* usuário cancelou */ }
                return;
            }
            try {
                await navigator.clipboard.writeText(data.url);
                label.textContent = 'Link copiado!';
            } catch (error) {
                label.textContent = 'Copie o link da barra';
            }
            window.setTimeout(() => { label.textContent = 'Compartilhar'; }, 2200);
        });
    }
}());
