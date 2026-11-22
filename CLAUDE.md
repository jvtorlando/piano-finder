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

Não há linter nem formatter configurado.

## Arquitetura

**Infraestrutura:** Django roda na Vercel (serverless). O banco de produção é PostgreSQL na Neon (`DATABASE_URL`), as imagens ficam no Cloudinary e os arquivos estáticos são servidos pelo WhiteNoise. O DNS é da Hostinger. Um push/merge na `main` dispara o deploy de produção na Vercel. O build (`[tool.vercel.scripts]` em `pyproject.toml`) só roda `migrate` quando `VERCEL_ENV=production` e existe `DATABASE_URL`. `build.sh` e `Procfile` são de uma hospedagem anterior (estilo Render/Heroku).

**Moderação:** `Piano.aprovado` e `Comentario.aprovado` começam `False`. Toda view pública filtra por `aprovado=True` (inclusive `get_object_or_404` no detalhe, nos votos e na avaliação). A aprovação acontece só no Django Admin (`pianos/admin.py`, ações em lote e `list_editable`). Qualquer nova consulta pública precisa manter esse filtro.

**Fotos (dois caminhos diferentes):**
- *Formulário público* (`adicionar.html`): o navegador recorta a imagem em 16:10 com `pianos/static/pianos/image-cropper.js`, exporta um JPEG 1600×1000 e envia **direto ao Cloudinary** usando o preset unsigned. Só as URLs voltam ao Django, em campos ocultos `foto_url_1..3`. `PianoForm._clean_cloudinary_url` aceita apenas `https://res.cloudinary.com/<CLOUD_NAME>/image/upload/...`. A view copia `foto_url_1` para o campo do model `foto_url` (o nome difere de propósito).
- *Admin*: `PianoAdminForm.upload_foto` recebe o arquivo (limite de 10 MB validado no servidor) e `PianoAdmin.save_model` faz o upload com `cloudinary.uploader.unsigned_upload`. O admin reaproveita o mesmo cropper via `admin-image-crop.js`. Falhas do Cloudinary são capturadas em `changeform_view` para não virar erro 500.
- O model guarda até três URLs (`foto_url`, `foto_url_2`, `foto_url_3`); use a property `Piano.fotos` para obter a lista sem vazios.

**Votos e avaliações** (`like_piano`, `avaliar_piano`): endpoints POST que respondem JSON, chamados por `fetch` em `detalhe.html`. Não há contas de usuário: o voto/nota de cada visitante fica na sessão (`voto_piano_<id>`, `estrelas_piano_<id>`). As atualizações usam `transaction.atomic()` + `select_for_update()`. A média de estrelas é recalculada de forma incremental e não existe tabela de avaliações individuais. Cada like recalcula `destaque` para os 3 pianos com mais likes. Não mude `destaque` manualmente esperando que persista.

**Rate limit:** `django-ratelimit` por IP em todas as views que recebem POST, com cache `LocMemCache`. Na Vercel isso não é compartilhado entre instâncias (limitação conhecida, listada no README). `Ratelimited` vira uma resposta 429 pelo `handler403` (`views.permission_denied`, template `403.html`).

**Templates:** cada template em `pianos/templates/pianos/` é uma página HTML completa e independente, com CSS e JS embutidos (não há `base.html`). Mudanças visuais comuns (fontes, cores, cabeçalho) precisam ser repetidas em cada arquivo. O único CSS/JS compartilhado é o do cropper em `pianos/static/pianos/`.

**Listas duplicadas:** UFs e tipos de piano estão definidos em mais de um lugar: `TIPO_PIANO_CHOICES` em `models.py`, `ESTADOS`/`TIPOS` em `views.py` (para os filtros) e o conjunto de UFs em `PianoForm.clean_estado`. Altere todos juntos.

**Migrations de dados:** a `0011` importa os pianos iniciais para a produção e só roda com `VERCEL_ENV=production`. A `0012` limpa esses dados. Elas não fazem nada localmente, então o banco local começa vazio: crie pianos pelo admin (`python manage.py createsuperuser`).

## Testes

Todos os testes estão em `pianos/tests.py`. `PianoFinderTests` aplica `override_settings` com um Cloudinary falso (`piano-finder-tests`) e limpa o cache no `setUp` para que o rate limit não vaze entre testes. Uploads para o Cloudinary são mockados com `patch`. Use os helpers `criar_piano()` e `dados_cadastro()` em novos testes.

## Fluxo de mudanças

O CHANGELOG segue Keep a Changelog e o projeto usa SemVer. Novas mudanças entram em `## [Unreleased]`, nas seções `Added`/`Changed`/`Fixed`/`Security`. As releases têm tag `vX.Y.Z` e uma GitHub Release. Pelo histórico, as mudanças chegam à `main` por pull request.
