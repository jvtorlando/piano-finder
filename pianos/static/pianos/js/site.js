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

    // Aviso rápido no topo da tela (usado para erros de requisições HTMX).
    function toast(message, tone = 'erro') {
        let container = document.querySelector('[data-toasts]');
        if (!container) {
            container = document.createElement('div');
            container.dataset.toasts = '';
            container.className = 'pointer-events-none fixed inset-x-0 top-20 z-50 flex flex-col items-center gap-2 px-4';
            document.body.appendChild(container);
        }
        const el = document.createElement('div');
        el.setAttribute('role', tone === 'erro' ? 'alert' : 'status');
        el.className = tone === 'erro'
            ? 'pointer-events-auto max-w-md animate-fade-up border border-danger/50 bg-ebony/95 px-5 py-3 text-center text-danger italic shadow-2xl shadow-black/60 backdrop-blur'
            : 'pointer-events-auto max-w-md animate-fade-up border border-gold/50 bg-ebony/95 px-5 py-3 text-center text-parchment italic shadow-2xl shadow-black/60 backdrop-blur';
        el.textContent = message;
        container.appendChild(el);
        window.setTimeout(() => el.remove(), 5000);
    }

    window.PianoFinder = { init, toast };

    document.addEventListener('DOMContentLoaded', () => {
        initNav();
        initToasts();
        init(document);
    });

    // HTMX: reaplica os comportamentos no HTML novo e trata erros de rede/servidor.
    document.addEventListener('htmx:load', event => init(event.detail.elt));
    document.addEventListener('htmx:historyRestore', () => init(document));
    document.addEventListener('htmx:responseError', event => {
        const status = event.detail.xhr.status;
        toast(status === 429
            ? 'Muitas tentativas seguidas. Espere alguns minutos e tente de novo.'
            : 'Algo deu errado. Tente de novo daqui a pouco.');
    });
    document.addEventListener('htmx:sendError', () => toast('Parece que a internet caiu. Confira a conexão.'));

    // Filtros vazios não entram na URL (?tipo=digital em vez de ?tipo=digital&cidade=&estado=).
    document.addEventListener('htmx:configRequest', event => {
        if (event.detail.verb !== 'get') return;
        const params = event.detail.parameters;
        for (const key of Object.keys(params)) {
            if (params[key] === '') delete params[key];
        }
    });

    // Depois que a URL muda (ex.: ao remover um filtro pelo "×"), a janela de
    // filtros passa a refletir os filtros da URL.
    document.addEventListener('htmx:pushedIntoHistory', () => {
        const form = document.querySelector('form[data-close-on-submit]');
        if (!form) return;
        const params = new URLSearchParams(window.location.search);
        form.querySelectorAll('input[type="radio"]').forEach(radio => {
            radio.checked = radio.value === (params.get(radio.name) || '');
        });
        form.querySelectorAll('input[type="search"], input[type="text"]').forEach(input => {
            input.value = params.get(input.name) || '';
        });
    });

    // Formulários com data-close-on-submit fecham a janela (<dialog>) em que estão.
    document.addEventListener('submit', event => {
        if (event.target.matches('[data-close-on-submit]')) event.target.closest('dialog')?.close();
    });
}());
