// Comportamentos compartilhados por todas as páginas públicas.
// Cada função é idempotente e pode ser chamada de novo depois que o HTMX
// trocar um pedaço da página (evento htmx:afterSwap).
(function () {
    'use strict';

    // Sombra no menu ao rolar a página.
    function initNav() {
        const nav = document.querySelector('[data-nav]');
        if (!nav) return;
        const update = () => nav.classList.toggle('shadow-xl', window.scrollY > 16);
        window.addEventListener('scroll', update, { passive: true });
        update();
    }

    // <dialog>: botões com data-open-dialog="id" abrem, data-close-dialog fecham.
    // Clicar fora da janela (no fundo escurecido) também fecha.
    function initDialogs(root) {
        root.querySelectorAll('[data-open-dialog]').forEach(button => {
            if (button.dataset.dialogBound) return;
            button.dataset.dialogBound = 'true';
            button.addEventListener('click', () => {
                const dialog = document.getElementById(button.dataset.openDialog);
                if (dialog && !dialog.open) dialog.showModal();
            });
        });
        root.querySelectorAll('dialog').forEach(dialog => {
            if (dialog.dataset.dialogBound) return;
            dialog.dataset.dialogBound = 'true';
            dialog.addEventListener('click', event => {
                if (event.target === dialog || event.target.closest('[data-close-dialog]')) dialog.close();
            });
        });
    }

    // Elementos com data-reveal aparecem suavemente ao entrar na tela.
    const revealObserver = 'IntersectionObserver' in window
        ? new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) return;
                entry.target.classList.add('is-visible');
                revealObserver.unobserve(entry.target);
            });
        }, { threshold: 0.06, rootMargin: '0px 0px -40px 0px' })
        : null;

    function initReveal(root) {
        root.querySelectorAll('[data-reveal]:not(.is-visible)').forEach((el, i) => {
            if (!revealObserver) { el.classList.add('is-visible'); return; }
            el.style.transitionDelay = `${(i % 3) * 70}ms`;
            revealObserver.observe(el);
        });
    }

    // Carrossel de fotos (rolagem nativa com scroll-snap) e seus pontinhos.
    function initCarousels(root) {
        root.querySelectorAll('[data-carousel]').forEach(track => {
            if (track.dataset.carouselBound) return;
            track.dataset.carouselBound = 'true';
            const dots = track.parentElement.querySelectorAll('[data-carousel-dots] > *');
            if (!dots.length) return;
            const update = () => {
                const index = Math.round(track.scrollLeft / track.clientWidth);
                dots.forEach((dot, i) => {
                    dot.classList.toggle('bg-gold', i === index);
                    dot.classList.toggle('scale-125', i === index);
                    dot.classList.toggle('bg-white/40', i !== index);
                });
            };
            track.addEventListener('scroll', update, { passive: true });
        });
        root.querySelectorAll('[data-carousel-step]').forEach(button => {
            if (button.dataset.stepBound) return;
            button.dataset.stepBound = 'true';
            button.addEventListener('click', () => {
                const track = document.getElementById(button.dataset.carouselStep);
                if (!track) return;
                const direction = Number(button.dataset.direction || 1);
                track.scrollBy({ left: direction * track.clientWidth, behavior: 'smooth' });
            });
        });
    }

    // Mensagens de sucesso somem sozinhas.
    function initToasts() {
        document.querySelectorAll('[data-toasts] > *').forEach(toast => {
            window.setTimeout(() => {
                toast.style.transition = 'opacity .4s, transform .4s';
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(-8px)';
                window.setTimeout(() => toast.remove(), 400);
            }, 5000);
        });
    }

    function init(root) {
        initDialogs(root);
        initReveal(root);
        initCarousels(root);
    }

    window.PianoFinder = { init };

    document.addEventListener('DOMContentLoaded', () => {
        initNav();
        initToasts();
        init(document);
    });

    document.addEventListener('htmx:afterSwap', event => init(event.detail.target));
}());
