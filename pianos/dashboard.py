"""Dados do painel inicial do admin (Unfold) e dos contadores do menu lateral."""

from django.db.models import Count, Sum
from django.urls import reverse

from .models import Comentario, Piano, TIPO_PIANO_CHOICES


def badge_pianos_pendentes(request):
    total = Piano.objects.filter(aprovado=False).count()
    return total or None


def badge_comentarios_pendentes(request):
    total = Comentario.objects.filter(aprovado=False).count()
    return total or None


def dashboard_callback(request, context):
    pianos = Piano.objects.all()
    aprovados = pianos.filter(aprovado=True)

    totais = aprovados.aggregate(likes=Sum('likes'), avaliacoes=Sum('total_avaliacoes'))
    pianos_pendentes = pianos.filter(aprovado=False).order_by('-data_cadastro')
    comentarios_pendentes = (
        Comentario.objects.filter(aprovado=False)
        .select_related('piano')
        .order_by('-data')
    )

    url_pianos = reverse('admin:pianos_piano_changelist')
    url_comentarios = reverse('admin:pianos_comentario_changelist')

    nomes_tipos = dict(TIPO_PIANO_CHOICES)
    total_aprovados = aprovados.count()
    por_tipo = [
        {
            'title': nomes_tipos.get(linha['tipo'], linha['tipo']),
            'description': linha['total'],
            'value': round(linha['total'] * 100 / total_aprovados) if total_aprovados else 0,
        }
        for linha in aprovados.values('tipo').annotate(total=Count('id')).order_by('-total')
    ]
    por_cidade = list(
        aprovados.values('cidade', 'estado')
        .annotate(total=Count('id'))
        .order_by('-total', 'cidade')[:6]
    )

    context.update({
        'indicadores': [
            {
                'titulo': 'Pianos publicados',
                'valor': total_aprovados,
                'icone': 'piano',
                'link': url_pianos + '?aprovado__exact=1',
            },
            {
                'titulo': 'Pianos aguardando',
                'valor': pianos_pendentes.count(),
                'icone': 'pending_actions',
                'link': url_pianos + '?aprovado__exact=0',
                'destaque': pianos_pendentes.exists(),
            },
            {
                'titulo': 'Comentários aguardando',
                'valor': comentarios_pendentes.count(),
                'icone': 'rate_review',
                'link': url_comentarios + '?aprovado__exact=0',
                'destaque': comentarios_pendentes.exists(),
            },
            {
                'titulo': 'Likes recebidos',
                'valor': totais['likes'] or 0,
                'icone': 'favorite',
                'link': url_pianos,
            },
        ],
        'pianos_pendentes': pianos_pendentes[:5],
        'comentarios_pendentes': comentarios_pendentes[:5],
        'pianos_por_tipo': por_tipo,
        'pianos_por_cidade': por_cidade,
        'total_avaliacoes': totais['avaliacoes'] or 0,
    })
    return context
