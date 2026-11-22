from django.conf import settings


def site(request):
    """Variáveis disponíveis em todos os templates."""
    return {
        # Vai no fim das URLs de JS/CSS (?v=...) para o navegador baixar a versão
        # nova depois de cada deploy, em vez de usar a antiga do cache.
        'static_version': settings.STATIC_VERSION,
        # Vercel Web Analytics e Speed Insights só são carregados em produção na Vercel.
        'vercel_analytics': settings.VERCEL_ANALYTICS,
    }
