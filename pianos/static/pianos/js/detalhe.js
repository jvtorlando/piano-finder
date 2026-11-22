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
                ? 'Muitas tentativas seguidas. Espere alguns minutos.'
                : (body.erro || 'Não deu certo. Tente de novo.');
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
    // As estrelas douradas mostram sempre a média (com frações). Passar o mouse
    // mostra a nota que será dada; depois de votar, a média é atualizada e a
    // nota da pessoa aparece no texto ao lado.
    const rating = document.querySelector('[data-rating-url]');
    if (rating) {
        const fill = rating.querySelector('[data-rating-fill]');
        const stars = [...rating.querySelectorAll('[data-star]')];
        const status = rating.querySelector('[data-rating-status]');
        const avg = rating.querySelector('[data-rating-avg]');
        const total = rating.querySelector('[data-rating-total]');
        const formatar = valor => valor.toLocaleString('pt-BR', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
        let media = Number(rating.dataset.media) || 0;
        let votou = Boolean(rating.dataset.minhaAvaliacao);

        const mostrar = valor => { fill.style.width = `${(valor / 5) * 100}%`; };
        const voltarParaMedia = () => { if (!votou) mostrar(media); };

        stars.forEach(star => {
            const valor = Number(star.dataset.star);
            star.addEventListener('mouseenter', () => { if (!votou) mostrar(valor); });
            star.addEventListener('focus', () => { if (!votou) mostrar(valor); });
            star.addEventListener('mouseleave', voltarParaMedia);
            star.addEventListener('blur', voltarParaMedia);
            star.addEventListener('click', async () => {
                if (votou) return;
                stars.forEach(s => { s.disabled = true; });
                try {
                    const data = await post(rating.dataset.ratingUrl, { estrelas: valor });
                    votou = true;
                    media = Number(data.estrelas);
                    mostrar(media);
                    avg.textContent = formatar(media);
                    const n = data.total_avaliacoes;
                    total.textContent = `(${n} ${n === 1 ? 'avaliação' : 'avaliações'})`;
                    stars.forEach(s => s.setAttribute('aria-checked', String(Number(s.dataset.star) === valor)));
                    status.textContent = `Sua nota: ${valor} de 5. Obrigado.`;
                    status.classList.replace('text-muted', 'text-gold');
                } catch (error) {
                    mostrar(media);
                    status.textContent = error.message;
                    stars.forEach(s => { s.disabled = false; });
                }
            });
        });
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
                label.textContent = 'Copie o link do navegador';
            }
            window.setTimeout(() => { label.textContent = 'Compartilhar'; }, 2200);
        });
    }
}());
