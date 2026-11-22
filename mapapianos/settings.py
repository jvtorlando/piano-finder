from pathlib import Path
import os

import cloudinary
import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


DEBUG = env_bool('DEBUG', default=False)
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-local-development-only'
    else:
        raise ImproperlyConfigured('SECRET_KEY is required when DEBUG is False.')

ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        'ALLOWED_HOSTS',
        '127.0.0.1,localhost,.vercel.app,pianofinder.com.br,www.pianofinder.com.br',
    ).split(',')
    if host.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get('CSRF_TRUSTED_ORIGINS', '').split(',')
    if origin.strip()
]

INSTALLED_APPS = [
    # O Unfold precisa vir antes de django.contrib.admin para sobrescrever os templates.
    'unfold',
    'unfold.contrib.filters',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'cloudinary',
    'cloudinary_storage',
    'django_ratelimit',
    'django_tailwind_cli',
    'pianos',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'mapapianos.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'mapapianos.wsgi.application'

def database_config():
    # Uma DATABASE_URL vazia (como no .env.example) conta como ausente e usa SQLite.
    url = os.environ.get('DATABASE_URL', '').strip()
    return dj_database_url.parse(
        url or f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )


DATABASES = {
    'default': database_config(),
}

if not DEBUG and not os.environ.get('DATABASE_URL', '').strip():
    raise ImproperlyConfigured('DATABASE_URL is required when DEBUG is False.')

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ── Arquivos estáticos ──────────────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# ── Tailwind ────────────────────────────────────────────────────────────────
# `python manage.py tailwind build` gera static/css/site.css a partir de
# assets/tailwind.css. O CSS gerado é commitado, então a Vercel não precisa do
# binário do Tailwind; rode o build sempre que mudar classes nos templates.
TAILWIND_CLI_SRC_CSS = 'assets/tailwind.css'
TAILWIND_CLI_DIST_CSS = 'css/site.css'
TAILWIND_CLI_VERSION = '4.3.5'

# ── Mídia ───────────────────────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'  # necessário mesmo usando Cloudinary

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Cloudinary ──────────────────────────────────────────────────────────────
CLOUDINARY_STORAGE = {
    'CLOUD_NAME': os.environ.get('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': os.environ.get('CLOUDINARY_API_KEY'),
    'API_SECRET': os.environ.get('CLOUDINARY_API_SECRET'),
}
CLOUDINARY_UPLOAD_PRESET = os.environ.get(
    'CLOUDINARY_UPLOAD_PRESET',
    'pianos_unsigned' if DEBUG else '',
)

if not DEBUG:
    required_cloudinary = {
        'CLOUDINARY_CLOUD_NAME': CLOUDINARY_STORAGE['CLOUD_NAME'],
        'CLOUDINARY_API_KEY': CLOUDINARY_STORAGE['API_KEY'],
        'CLOUDINARY_API_SECRET': CLOUDINARY_STORAGE['API_SECRET'],
        'CLOUDINARY_UPLOAD_PRESET': CLOUDINARY_UPLOAD_PRESET,
    }
    missing_cloudinary = [
        name for name, value in required_cloudinary.items() if not value
    ]
    if missing_cloudinary:
        raise ImproperlyConfigured(
            'Missing production settings: ' + ', '.join(missing_cloudinary)
        )

cloudinary.config(
    cloud_name=CLOUDINARY_STORAGE['CLOUD_NAME'],
    api_key=CLOUDINARY_STORAGE['API_KEY'],
    api_secret=CLOUDINARY_STORAGE['API_SECRET'],
)

STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        # CompressedStaticFilesStorage (sem Manifest) é mais seguro —
        # o Manifest quebra se collectstatic não foi rodado ainda
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'piano-finder-rate-limit',
    },
}
RATELIMIT_USE_CACHE = 'default'

# O Procfile inicia um único worker do Gunicorn, então o cache local mantém os
# contadores consistentes. Ao usar mais workers, migre o cache para Redis.
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']

# ── Segurança em produção ───────────────────────────────────────────────────
if not DEBUG:
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env_bool('SECURE_SSL_REDIRECT', default=True)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# ── Logging de erros em produção (sem expor DEBUG) ─────────────────────────
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
        },
    },
}

# ── Admin (Unfold) ──────────────────────────────────────────────────────────
from django.templatetags.static import static  # noqa: E402
from django.urls import reverse, reverse_lazy  # noqa: E402

UNFOLD = {
    'SITE_TITLE': 'Piano Finder',
    'SITE_HEADER': 'Piano Finder',
    'SITE_SUBHEADER': 'Moderação',
    'SITE_URL': '/',
    'SITE_SYMBOL': 'piano',
    'SITE_FAVICONS': [
        {'rel': 'icon', 'type': 'image/png', 'href': lambda request: static('favicon.png')},
    ],
    'SHOW_HISTORY': True,
    'SHOW_VIEW_ON_SITE': True,
    'DASHBOARD_CALLBACK': 'pianos.dashboard.dashboard_callback',
    'BORDER_RADIUS': '8px',
    'COLORS': {
        # Neutros quentes, puxando para o marfim do site.
        'base': {
            '50': 'oklch(98.5% .004 80)',
            '100': 'oklch(96% .008 80)',
            '200': 'oklch(91.5% .01 80)',
            '300': 'oklch(85% .012 80)',
            '400': 'oklch(70% .014 80)',
            '500': 'oklch(55% .014 80)',
            '600': 'oklch(45% .012 80)',
            '700': 'oklch(36% .01 80)',
            '800': 'oklch(26% .006 80)',
            '900': 'oklch(20% .004 80)',
            '950': 'oklch(14% .002 80)',
        },
        # Dourado do site (#c9a84c ≈ oklch(74% .117 89.5)).
        'primary': {
            '50': 'oklch(98% .02 90)',
            '100': 'oklch(95% .045 90)',
            '200': 'oklch(90% .075 90)',
            '300': 'oklch(84.5% .11 90)',
            '400': 'oklch(79% .12 90)',
            '500': 'oklch(74.3% .117 89.5)',
            '600': 'oklch(64% .11 85)',
            '700': 'oklch(54% .095 82)',
            '800': 'oklch(45% .08 80)',
            '900': 'oklch(38% .065 78)',
            '950': 'oklch(27% .045 76)',
        },
    },
    'SIDEBAR': {
        'show_search': True,
        'show_all_applications': False,
        'navigation': [
            {
                'title': 'Moderação',
                'separator': True,
                'items': [
                    {
                        'title': 'Painel',
                        'icon': 'dashboard',
                        'link': reverse_lazy('admin:index'),
                    },
                    {
                        'title': 'Pianos pendentes',
                        'icon': 'pending_actions',
                        'link': lambda request: reverse('admin:pianos_piano_changelist') + '?aprovado__exact=0',
                        'badge': 'pianos.dashboard.badge_pianos_pendentes',
                    },
                    {
                        'title': 'Comentários pendentes',
                        'icon': 'rate_review',
                        'link': lambda request: reverse('admin:pianos_comentario_changelist') + '?aprovado__exact=0',
                        'badge': 'pianos.dashboard.badge_comentarios_pendentes',
                    },
                ],
            },
            {
                'title': 'Catálogo',
                'separator': True,
                'items': [
                    {
                        'title': 'Todos os pianos',
                        'icon': 'piano',
                        'link': reverse_lazy('admin:pianos_piano_changelist'),
                    },
                    {
                        'title': 'Todos os comentários',
                        'icon': 'forum',
                        'link': reverse_lazy('admin:pianos_comentario_changelist'),
                    },
                ],
            },
            {
                'title': 'Acesso',
                'separator': True,
                'collapsible': True,
                'items': [
                    {
                        'title': 'Usuários',
                        'icon': 'person',
                        'link': reverse_lazy('admin:auth_user_changelist'),
                    },
                    {
                        'title': 'Grupos',
                        'icon': 'group',
                        'link': reverse_lazy('admin:auth_group_changelist'),
                    },
                ],
            },
        ],
    },
}
