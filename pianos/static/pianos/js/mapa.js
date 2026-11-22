// Mapas com Leaflet: o mapa geral (/mapa/) e o mapinha da página de detalhe.
(function () {
    'use strict';

    // Tiles oficiais do OpenStreetMap (gratuitos, exigem atribuição). O tema escuro
    // vem de um filtro CSS (.pf-tiles-escuros em assets/tailwind.css).
    const TILES = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
    const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
    const BRASIL = [[-33.8, -73.99], [5.3, -34.8]];

    function pin(destaque) {
        return L.divIcon({
            className: '',
            html: `<span class="block size-7 -translate-y-1/2 rounded-full rounded-br-none rotate-45 border border-ink ${destaque ? 'bg-gold-light' : 'bg-gold'} shadow-lg shadow-black/60"><span class="m-auto mt-[7px] block size-2.5 rounded-full bg-ink"></span></span>`,
            iconSize: [28, 28],
            iconAnchor: [14, 28],
            popupAnchor: [0, -30],
        });
    }

    const pinUsuario = () => L.divIcon({
        className: '',
        html: '<span class="block size-4 rounded-full border-2 border-white bg-sky-500 shadow-[0_0_0_6px_rgba(14,165,233,0.25)]"></span>',
        iconSize: [16, 16],
        iconAnchor: [8, 8],
    });

    function escapeHtml(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }

    function popupHtml(p) {
        const foto = p.foto
            ? `<img src="${escapeHtml(p.foto)}" alt="" class="mb-3 aspect-[16/10] w-full object-cover" loading="lazy">`
            : '';
        const nota = p.estrelas ? `<span><span class="text-gold">★</span> ${p.estrelas.toFixed(1)}</span>` : '';
        const situacao = p.funcionando
            ? '<span class="text-ok">Funcionando</span>'
            : '<span class="text-danger">Em manutenção</span>';
        return `${foto}
            <div class="text-[0.62rem] tracking-[0.22em] text-gold uppercase">${escapeHtml(p.tipo)} · ${escapeHtml(p.cidade)}/${escapeHtml(p.estado)}</div>
            <div class="mt-1 font-display text-xl leading-tight font-medium text-ivory">${escapeHtml(p.nome)}</div>
            <div class="mt-0.5 text-sm text-muted italic">${escapeHtml(p.endereco)}</div>
            <div class="mt-2 flex gap-3 text-sm italic">${situacao}${nota}</div>
            <a href="${escapeHtml(p.url)}" class="mt-3 block border border-gold px-3 py-2 text-center text-[0.72rem] tracking-[0.2em] !text-gold-light uppercase hover:bg-gold hover:!text-ink">Ver o piano</a>`;
    }

    function criarMapa(el, opcoes = {}) {
        const mapa = L.map(el, {
            zoomControl: true,
            scrollWheelZoom: opcoes.scrollWheelZoom ?? true,
            attributionControl: true,
        });
        L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 19, className: 'pf-tiles-escuros' }).addTo(mapa);
        mapa.fitBounds(BRASIL);
        return mapa;
    }

    // Distância em km entre dois pontos (fórmula de haversine).
    function distanciaKm(a, b) {
        const rad = x => x * Math.PI / 180;
        const dLat = rad(b.lat - a.lat);
        const dLng = rad(b.lng - a.lng);
        const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
        return 6371 * 2 * Math.asin(Math.sqrt(h));
    }

    function formatarDistancia(km) {
        return km < 1 ? `${Math.round(km * 1000)} m` : `${km.toLocaleString('pt-BR', { maximumFractionDigits: km < 10 ? 1 : 0 })} km`;
    }

    // ── Mapa geral ──
    function iniciarMapaGeral() {
        const el = document.getElementById('mapa-geral');
        const dados = document.getElementById('pontos-mapa');
        if (!el || !dados) return;

        const pontos = JSON.parse(dados.textContent);
        const mapa = criarMapa(el);
        const lista = document.getElementById('lista-mapa');
        const marcadores = new Map();

        pontos.forEach(p => {
            const marcador = L.marker([p.lat, p.lng], { icon: pin(false), title: p.nome })
                .bindPopup(popupHtml(p), { maxWidth: 260, minWidth: 220 })
                .addTo(mapa);
            marcadores.set(p.id, marcador);
        });

        if (pontos.length) {
            mapa.fitBounds(L.latLngBounds(pontos.map(p => [p.lat, p.lng])).pad(0.25), { maxZoom: 15 });
        }

        function focar(id) {
            const marcador = marcadores.get(id);
            if (!marcador) return;
            mapa.flyTo(marcador.getLatLng(), Math.max(mapa.getZoom(), 16), { duration: 0.8 });
            marcador.openPopup();
            if (window.matchMedia('(max-width: 767px)').matches) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }

        lista?.addEventListener('click', event => {
            const item = event.target.closest('[data-ponto]');
            if (item) focar(Number(item.dataset.ponto));
        });

        // ?piano=ID abre direto aquele piano (link vindo da página de detalhe).
        const inicial = Number(new URLSearchParams(window.location.search).get('piano'));
        if (inicial) window.setTimeout(() => focar(inicial), 300);

        // ── Perto de mim ──
        const botao = document.getElementById('perto-de-mim');
        const status = document.getElementById('status-localizacao');
        let marcadorUsuario = null;

        botao?.addEventListener('click', () => {
            if (!('geolocation' in navigator)) {
                status.textContent = 'Este navegador não informa a localização.';
                return;
            }
            botao.disabled = true;
            status.textContent = 'Procurando onde você está...';
            navigator.geolocation.getCurrentPosition(posicao => {
                botao.disabled = false;
                const eu = { lat: posicao.coords.latitude, lng: posicao.coords.longitude };
                if (marcadorUsuario) marcadorUsuario.remove();
                marcadorUsuario = L.marker([eu.lat, eu.lng], { icon: pinUsuario(), title: 'Você está aqui', zIndexOffset: 1000 }).addTo(mapa);

                const ordenados = pontos
                    .map(p => ({ ...p, km: distanciaKm(eu, p) }))
                    .sort((a, b) => a.km - b.km);

                // Reordena a lista e mostra a distância de cada piano.
                ordenados.forEach(p => {
                    const item = lista?.querySelector(`[data-ponto="${p.id}"]`);
                    if (!item) return;
                    item.querySelector('[data-distancia]').textContent = formatarDistancia(p.km);
                    lista.appendChild(item.closest('li'));
                });

                const maisProximos = ordenados.slice(0, 3).map(p => [p.lat, p.lng]);
                mapa.fitBounds(L.latLngBounds([[eu.lat, eu.lng], ...maisProximos]).pad(0.3), { maxZoom: 15 });
                status.textContent = ordenados.length
                    ? `O mais perto fica a ${formatarDistancia(ordenados[0].km)} daqui.`
                    : 'Nenhum piano no mapa ainda.';
            }, erro => {
                botao.disabled = false;
                status.textContent = erro.code === erro.PERMISSION_DENIED
                    ? 'Para ver os pianos mais perto, permita o acesso à localização.'
                    : 'Não consegui descobrir sua localização agora. Tente de novo em instantes.';
            }, { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 });
        });
    }

    // ── Mapinha da página de detalhe ──
    function iniciarMapaDetalhe() {
        const el = document.getElementById('mapa-piano');
        if (!el) return;
        const lat = Number(el.dataset.lat);
        const lng = Number(el.dataset.lng);
        const mapa = criarMapa(el, { scrollWheelZoom: false });
        mapa.setView([lat, lng], 16);
        L.marker([lat, lng], { icon: pin(false), title: el.dataset.nome }).addTo(mapa);
    }

    document.addEventListener('DOMContentLoaded', () => {
        if (!window.L) return;
        iniciarMapaGeral();
        iniciarMapaDetalhe();
    });
}());
