from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from django_ratelimit.exceptions import Ratelimited

from .models import ESTADOS, TIPO_PIANO_CHOICES, Comentario, Piano
from .forms import PianoForm, ComentarioForm


def _eh_htmx(request):
    return request.headers.get('HX-Request') == 'true'


def _filtros_aplicados(request, estado, cidade, tipo):
    """Rótulos dos filtros ativos, cada um com a URL da lista sem aquele filtro."""
    nomes_tipos = dict(TIPO_PIANO_CHOICES)
    nomes_estados = dict(ESTADOS)
    filtros = []
    for chave, valor, rotulo in (
        ('tipo', tipo, nomes_tipos.get(tipo, tipo)),
        ('cidade', cidade, cidade),
        ('estado', estado, nomes_estados.get(estado, estado)),
    ):
        if not valor:
            continue
        params = request.GET.copy()
        params.pop(chave, None)
        consulta = params.urlencode()
        filtros.append({
            'rotulo': rotulo,
            'remover_url': reverse('home') + (f'?{consulta}' if consulta else ''),
        })
    return filtros


def lista_pianos(request):
    publicados = Piano.objects.filter(aprovado=True)
    pianos = publicados.order_by('ordem', '-likes', '-data_cadastro')

    estado = request.GET.get('estado', '').strip().upper()
    cidade = request.GET.get('cidade', '').strip()
    tipo   = request.GET.get('tipo', '').strip()

    if estado:
        pianos = pianos.filter(estado__iexact=estado)
    if cidade:
        pianos = pianos.filter(cidade__icontains=cidade)
    if tipo:
        pianos = pianos.filter(tipo__iexact=tipo)

    filtros_ativos = bool(estado or cidade or tipo)

    # Filtros feitos via HTMX recebem só o bloco de resultados, não a página inteira.
    template = 'pianos/lista.html#resultados' if _eh_htmx(request) else 'pianos/lista.html'
    resposta = render(request, template, {
        'pianos': pianos,
        'estados': ESTADOS,
        'tipos': TIPO_PIANO_CHOICES,
        'estado_sel': estado,
        'cidade_sel': cidade,
        'tipo_sel': tipo,
        'filtros_ativos': filtros_ativos,
        'filtros_aplicados': _filtros_aplicados(request, estado, cidade, tipo),
        'total_publicados': publicados.count(),
        'total_cidades': publicados.values('cidade', 'estado').distinct().count(),
    })
    # A mesma URL devolve HTML diferente com e sem HTMX; caches precisam distinguir.
    patch_vary_headers(resposta, ['HX-Request'])
    return resposta


@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def adicionar_piano(request):
    if request.method == 'POST':
        form = PianoForm(request.POST)
        if form.is_valid():
            piano = form.save(commit=False)
            piano.foto_url = form.cleaned_data.get('foto_url_1') or None
            piano.foto_url_2 = form.cleaned_data.get('foto_url_2') or None
            piano.foto_url_3 = form.cleaned_data.get('foto_url_3') or None
            piano.save()
            messages.success(request, 'Sua sugestão foi enviada! Ela será analisada e publicada em breve.')
            return redirect('home')
    else:
        form = PianoForm()

    # O formulário escolhe o tipo em duas etapas: categoria e, se acústico, armário ou cauda.
    tipo_atual = form['tipo'].value() or ''
    return render(request, 'pianos/adicionar.html', {
        'form': form,
        'tipos_categoria': [('acustico', 'Acústico'), ('digital', 'Digital'), ('hibrido', 'Híbrido')],
        'tipos_acustico': [('armario', 'Armário'), ('cauda', 'Cauda')],
        'categoria_inicial': tipo_atual if tipo_atual in {'digital', 'hibrido'} else 'acustico',
        'subtipo_inicial': 'cauda' if tipo_atual == 'cauda' else 'armario',
        'cloudinary_cloud_name': settings.CLOUDINARY_STORAGE.get('CLOUD_NAME', ''),
        'cloudinary_upload_preset': settings.CLOUDINARY_UPLOAD_PRESET,
    })


@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def detalhe_piano(request, piano_id):
    piano = get_object_or_404(Piano, id=piano_id, aprovado=True)
    comentarios = piano.comentarios.filter(aprovado=True).order_by('-data')
    form = ComentarioForm()

    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        enviado = form.is_valid()
        if enviado:
            comentario = form.save(commit=False)
            comentario.piano = piano
            comentario.save()

        if _eh_htmx(request):
            # O HTMX troca só o formulário: limpo e com aviso se deu certo, com erros se não.
            return render(request, 'pianos/detalhe.html#form_comentario', {
                'piano': piano,
                'form': ComentarioForm() if enviado else form,
                'comentario_enviado': enviado,
            })
        if enviado:
            messages.success(request, 'Comentário enviado! Será publicado após moderação.')
            return redirect('detalhe_piano', piano_id=piano_id)

    return render(request, 'pianos/detalhe.html', {
        'piano': piano,
        'comentarios': comentarios,
        'form': form,
        'voto_atual': request.session.get(f'voto_piano_{piano_id}'),
        'minha_avaliacao': request.session.get(f'estrelas_piano_{piano_id}'),
    })


@require_POST
@ratelimit(key='ip', rate='60/h', method='POST', block=True)
def like_piano(request, piano_id):
    acao = request.POST.get('acao')
    if acao not in {'like', 'dislike'}:
        return JsonResponse({'erro': 'Ação de voto inválida.'}, status=400)

    session_key = f'voto_piano_{piano_id}'
    voto_atual = request.session.get(session_key)

    with transaction.atomic():
        piano = get_object_or_404(
            Piano.objects.select_for_update(),
            id=piano_id,
            aprovado=True,
        )

        if acao == 'like':
            if voto_atual == 'like':
                piano.likes = max(0, piano.likes - 1)
                request.session.pop(session_key, None)
                voto_atual = None
            else:
                if voto_atual == 'dislike':
                    piano.dislikes = max(0, piano.dislikes - 1)
                piano.likes += 1
                request.session[session_key] = 'like'
                voto_atual = 'like'
        else:
            if voto_atual == 'dislike':
                piano.dislikes = max(0, piano.dislikes - 1)
                request.session.pop(session_key, None)
                voto_atual = None
            else:
                if voto_atual == 'like':
                    piano.likes = max(0, piano.likes - 1)
                piano.dislikes += 1
                request.session[session_key] = 'dislike'
                voto_atual = 'dislike'

        piano.save(update_fields=['likes', 'dislikes'])

        top_ids = list(
            Piano.objects.filter(aprovado=True, likes__gt=0)
            .order_by('-likes', '-data_cadastro')
            .values_list('id', flat=True)[:3]
        )
        Piano.objects.filter(aprovado=True, destaque=True).exclude(id__in=top_ids).update(destaque=False)
        Piano.objects.filter(id__in=top_ids, destaque=False).update(destaque=True)

    return JsonResponse({
        'likes': piano.likes,
        'dislikes': piano.dislikes,
        'voto_atual': voto_atual,
    })


@require_POST
@ratelimit(key='ip', rate='20/h', method='POST', block=True)
def avaliar_piano(request, piano_id):
    session_key = f'estrelas_piano_{piano_id}'

    if request.session.get(session_key):
        return JsonResponse({'erro': 'Você já avaliou este piano.'}, status=400)

    try:
        estrelas = int(request.POST.get('estrelas', 0))
        if not 1 <= estrelas <= 5:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'erro': 'Avaliação inválida.'}, status=400)

    with transaction.atomic():
        piano = get_object_or_404(
            Piano.objects.select_for_update(),
            id=piano_id,
            aprovado=True,
        )
        total = piano.total_avaliacoes
        nova_media = ((piano.estrelas * total) + estrelas) / (total + 1)
        piano.estrelas = round(nova_media, 2)
        piano.total_avaliacoes = total + 1
        piano.save(update_fields=['estrelas', 'total_avaliacoes'])

    request.session[session_key] = estrelas

    return JsonResponse({
        'estrelas': piano.estrelas,
        'total_avaliacoes': piano.total_avaliacoes,
        'minha_avaliacao': estrelas,
    })


def permission_denied(request, exception):
    limite_excedido = isinstance(exception, Ratelimited)
    return render(request, 'pianos/403.html', {
        'limite_excedido': limite_excedido,
    }, status=429 if limite_excedido else 403)
