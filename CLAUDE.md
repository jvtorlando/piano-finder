# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Visão geral

Piano Finder (www.pianofinder.com.br) é um catálogo colaborativo de pianos públicos no Brasil. É um projeto Django 6 / Python 3.14 com um único app (`pianos`) e o projeto de configuração `mapapianos`. Também é um projeto de portfólio do autor, então README e CHANGELOG são vitrine: mantenha os dois em inglês e atualizados quando uma mudança for visível ao usuário.

O código, os nomes de modelos/campos/views, os textos da interface e os testes estão em **português**. Siga esse padrão.

## Comandos

Ambiente local (Windows/PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env   # com DEBUG=True, os placeholders já bastam para rodar
python manage.py migrate
python manage.py runserver
```

Sem `DATABASE_URL`, ou com ela vazia, o Django usa SQLite (`db.sqlite3`), via `database_config()` em `settings.py`. Com `DEBUG=True` não é preciso `SECRET_KEY` real; com `DEBUG=False` o `settings.py` falha na inicialização se faltar `SECRET_KEY`, `DATABASE_URL` ou qualquer configuração do Cloudinary.

Testes e verificações (é exatamente o que o CI roda em `.github/workflows/tests.yml`):

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run   # falha se um model mudou sem migration
python manage.py test
python manage.py test pianos.tests.PianoFinderTests.test_like_alterna_sem_ficar_negativo   # um teste só
```

CSS (depois de mexer em classes Tailwind):

```powershell
python manage.py tailwind build   # gera static/css/site.css (commitar)
python manage.py tailwind watch   # recompila ao salvar
```

Não há linter nem formatter configurado.

## Arquitetura

**Infraestrutura:** Django roda na Vercel (serverless). O banco de produção é PostgreSQL na Neon (`DATABASE_URL`), as imagens ficam no Cloudinary e os arquivos estáticos são servidos pelo WhiteNoise. O DNS é da Hostinger. Um push/merge na `main` dispara o deploy de produção na Vercel. O build (`[tool.vercel.scripts]` em `pyproject.toml`) só roda `migrate` quando `VERCEL_ENV=production` e existe `DATABASE_URL`. `build.sh` e `Procfile` são de uma hospedagem anterior (estilo Render/Heroku).

**Moderação:** `Piano.aprovado` e `Comentario.aprovado` começam `False`. Toda view pública filtra por `aprovado=True` (inclusive `get_object_or_404` no detalhe, nos votos e na avaliação). A aprovação acontece só no Django Admin. Qualquer nova consulta pública precisa manter esse filtro.

**Admin (Unfold):** o admin usa o tema [django-unfold](https://unfoldadmin.com/). `'unfold'` precisa ficar antes de `django.contrib.admin` em `INSTALLED_APPS`. Os `ModelAdmin`/`TabularInline` vêm de `unfold.admin`, e as colunas e ações usam os decorators `unfold.decorators.display`/`action`. A configuração visual (cores douradas, menu lateral e badges de pendentes) fica no dict `UNFOLD` em `settings.py`. O painel inicial é `pianos/templates/admin/pianos_dashboard.html`, alimentado por `pianos/dashboard.py`, e o layout dele está em `pianos/static/pianos/admin-dashboard.css`. Use CSS próprio nesse arquivo: o CSS do Unfold vem pré-compilado e não inclui classes Tailwind que ele mesmo não usa, como `md:grid-cols-2`. `format_html` sem argumentos quebra no Django 6, então use `mark_safe` para HTML fixo.

Para ter dados no banco local, rode `python manage.py carregar_exemplos`, que só funciona com `DEBUG=True`.

**Fotos (dois caminhos diferentes):**
- *Formulário público* (`adicionar.html`): o navegador recorta a imagem em 16:10 com `pianos/static/pianos/image-cropper.js`, exporta um JPEG 1600×1000 e envia **direto ao Cloudinary** usando o preset unsigned. Só as URLs voltam ao Django, em campos ocultos `foto_url_1..3`. `PianoForm._clean_cloudinary_url` aceita apenas `https://res.cloudinary.com/<CLOUD_NAME>/image/upload/...`. A view copia `foto_url_1` para o campo do model `foto_url` (o nome difere de propósito).
- *Admin*: `PianoAdminForm.upload_foto` recebe o arquivo (limite de 10 MB validado no servidor) e `PianoAdmin.save_model` faz o upload com `cloudinary.uploader.unsigned_upload`. O admin reaproveita o mesmo cropper via `admin-image-crop.js`. Falhas do Cloudinary são capturadas em `changeform_view` para não virar erro 500.
- O model guarda até três URLs (`foto_url`, `foto_url_2`, `foto_url_3`); use a property `Piano.fotos` para obter a lista sem vazios.

**Votos e avaliações** (`like_piano`, `avaliar_piano`): endpoints POST que respondem JSON, chamados por `fetch` em `detalhe.html`. Não há contas de usuário: o voto/nota de cada visitante fica na sessão (`voto_piano_<id>`, `estrelas_piano_<id>`). As atualizações usam `transaction.atomic()` + `select_for_update()`. A média de estrelas é recalculada de forma incremental e não existe tabela de avaliações individuais. Cada like recalcula `destaque` para os 3 pianos com mais likes. Não mude `destaque` manualmente esperando que persista.

**Rate limit:** `django-ratelimit` por IP em todas as views que recebem POST, com cache `LocMemCache`. Na Vercel isso não é compartilhado entre instâncias (limitação conhecida, listada no README). `Ratelimited` vira uma resposta 429 pelo `handler403` (`views.permission_denied`, template `403.html`).

**Templates e CSS:** todas as páginas públicas estendem `pianos/templates/pianos/base.html`, que contém `<head>`, metatags de compartilhamento (blocos `og_*`), menu (bloco `nav_actions`), mensagens e rodapé. O CSS é **Tailwind v4** via `django-tailwind-cli`: a fonte é `assets/tailwind.css`, com os tokens de cor e fonte em `@theme` (`ink`, `ebony`, `ivory`, `gold`, `muted`…) e componentes como `.btn-gold`, `.chip`, `.field-input` e `.eyebrow`. A saída é `static/css/site.css`, **commitada**, porque a Vercel não roda o binário do Tailwind. Sempre que mudar classes em templates, JS ou `forms.py`, rode `python manage.py tailwind build`, ou `tailwind watch` enquanto edita, e commite o `site.css`. O Tailwind só procura classes nos caminhos `@source` de `assets/tailwind.css`, então classes montadas por concatenação de strings não são detectadas.

Os pedaços reaproveitados usam *template partials* do Django 6: `{% partialdef nome %}` / `{% partial nome %}`. Por exemplo, o card do piano e o bloco `resultados` em `lista.html`. O ícone de cada tipo de piano é `partials/tipo_icone.html`. O JavaScript fica em `pianos/static/pianos/js/`: `site.js` cuida de diálogos, carrossel e animações de entrada (`data-reveal`) e expõe `PianoFinder.init(root)` para reaplicar tudo após trocas de HTML; `detalhe.js` cuida de curtir, avaliar e compartilhar; `adicionar.js`, do recorte e do upload.

**HTMX:** a biblioteca fica em `pianos/static/pianos/vendor/htmx.min.js` (versão 2.0.11, sem CDN). Quando o pedido tem o cabeçalho `HX-Request`, as views devolvem só um partial, e não a página inteira: `lista_pianos` devolve `pianos/lista.html#resultados` (com `Vary: HX-Request`) e o POST de comentário em `detalhe_piano` devolve `pianos/detalhe.html#form_comentario`. Sem HTMX, tudo continua funcionando com formulários e links normais. Curtir e avaliar continuam como `fetch` com respostas JSON (`detalhe.js`). O `site.js` mostra um aviso para erros HTMX, como o 429 do rate limit, tira parâmetros vazios das URLs de filtro e sincroniza a janela de filtros com a URL.

**Mapa:** `Piano.latitude`/`longitude` (Decimal, opcionais; property `tem_coordenadas`). As coordenadas vêm de `pianos/geocoding.py`, que usa o Nominatim/OpenStreetMap com no máximo 1 requisição por segundo e User-Agent próprio. A busca **só** acontece no admin: em `PianoAdmin.save_model`, quando faltam coordenadas ou o endereço mudou e ninguém digitou lat/lon à mão; na ação em lote `buscar_coordenadas`, que processa até 8 pianos por vez; e ao aprovar. Nos testes, sempre aplique `patch('pianos.admin.geocodificar')`. A página `/mapa/` (`views.mapa_pianos`) envia os pontos via `json_script`, e `pianos/static/pianos/js/mapa.js` desenha o mapa geral, o "Perto de mim" (geolocalização do navegador + haversine, tudo no cliente) e o mapinha do detalhe. O Leaflet 1.9.4 fica em `pianos/static/pianos/vendor/leaflet/`. Os tiles são os do OpenStreetMap, escurecidos por CSS (`.pf-tiles-escuros`). Os tiles escuros do CARTO passaram a exigir chave de API.

**Listas de domínio:** UFs (`ESTADOS`, `UFS`) e tipos (`TIPO_PIANO_CHOICES`) ficam só em `pianos/models.py`. Views, formulário e filtros importam de lá.

**Migrations de dados:** a `0011` importa os pianos iniciais para a produção e só roda com `VERCEL_ENV=production`. A `0012` limpa esses dados. Elas não fazem nada localmente, então o banco local começa vazio. Use `carregar_exemplos` e `createsuperuser`.

## Testes

Todos os testes estão em `pianos/tests.py`. `PianoFinderTests` aplica `override_settings` com um Cloudinary falso (`piano-finder-tests`) e limpa o cache no `setUp` para que o rate limit não vaze entre testes. Uploads para o Cloudinary são mockados com `patch`. Use os helpers `criar_piano()` e `dados_cadastro()` em novos testes.

## Fluxo de mudanças

O CHANGELOG segue Keep a Changelog e o projeto usa SemVer. Novas mudanças entram em `## [Unreleased]`, nas seções `Added`/`Changed`/`Fixed`/`Security`. As releases têm tag `vX.Y.Z` e uma GitHub Release. Pelo histórico, as mudanças chegam à `main` por pull request.
