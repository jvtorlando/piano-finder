from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import Piano, Comentario
from .forms import PianoForm, ComentarioForm
import cloudinary.uploader

ESTADOS = [
    ('AC','Acre'), ('AL','Alagoas'), ('AP','Amapá'), ('AM','Amazonas'),
    ('BA','Bahia'), ('CE','Ceará'), ('DF','Distrito Federal'), ('ES','Espírito Santo'),
    ('GO','Goiás'), ('MA','Maranhão'), ('MT','Mato Grosso'), ('MS','Mato Grosso do Sul'),
    ('MG','Minas Gerais'), ('PA','Pará'), ('PB','Paraíba'), ('PR','Paraná'),
    ('PE','Pernambuco'), ('PI','Piauí'), ('RJ','Rio de Janeiro'), ('RN','Rio Grande do Norte'),
    ('RS','Rio Grande do Sul'), ('RO','Rondônia'), ('RR','Roraima'), ('SC','Santa Catarina'),
    ('SP','São Paulo'), ('SE','Sergipe'), ('TO','Tocantins'),
]

TIPOS = [
    ('acustico', 'Acústico'),
    ('cauda', 'Cauda'),
    ('armario', 'Armário'),
    ('digital', 'Digital'),
    ('hibrido', 'Híbrido'),
]

def lista_pianos(request):
    pianos = Piano.objects.filter(aprovado=True).order_by('ordem', '-likes', '-data_cadastro')

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

    return render(request, 'pianos/lista.html', {
        'pianos': pianos,
        'estados': ESTADOS,
        'tipos': TIPOS,
        'estado_sel': estado,
        'cidade_sel': cidade,
        'tipo_sel': tipo,
        'filtros_ativos': filtros_ativos,
    })


def adicionar_piano(request):
    if request.method == 'POST':
        form = PianoForm(request.POST, request.FILES)
        if form.is_valid():
            piano = form.save(commit=False)
            for campo, attr in [('foto', 'foto_url'), ('foto_2', 'foto_url_2'), ('foto_3', 'foto_url_3')]:
                arquivo = request.FILES.get(campo)
                if arquivo:
                    resultado = cloudinary.uploader.upload(arquivo, folder='pianos/')
                    setattr(piano, attr, resultado['secure_url'])
            piano.save()
            messages.success(request, 'Sua sugestão foi enviada! Ela será analisada e publicada em breve.')
            return redirect('home')
    else:
        form = PianoForm()
    return render(request, 'pianos/adicionar.html', {'form': form})


def detalhe_piano(request, piano_id):
    piano = get_object_or_404(Piano, id=piano_id, aprovado=True)
    comentarios = piano.comentarios.filter(aprovado=True).order_by('-data')
    form = ComentarioForm()

    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.piano = piano
            comentario.save()
            messages.success(request, 'Comentário enviado! Será publicado após moderação.')
            return redirect('detalhe_piano', piano_id=piano_id)

    return render(request, 'pianos/detalhe.html', {
        'piano': piano,
        'comentarios': comentarios,
        'form': form,
    })


@require_POST
def like_piano(request, piano_id):
    piano = get_object_or_404(Piano, id=piano_id, aprovado=True)
    acao = request.POST.get('acao')  # 'like' ou 'dislike'

    # Controle por sessão para evitar múltiplos votos
    session_key = f'voto_piano_{piano_id}'
    voto_atual = request.session.get(session_key)

    if acao == 'like':
        if voto_atual == 'like':
            # Remove like
            piano.likes = max(0, piano.likes - 1)
            del request.session[session_key]
            voto_atual = None
        else:
            if voto_atual == 'dislike':
                piano.dislikes = max(0, piano.dislikes - 1)
            piano.likes += 1
            request.session[session_key] = 'like'
            voto_atual = 'like'
    elif acao == 'dislike':
        if voto_atual == 'dislike':
            piano.dislikes = max(0, piano.dislikes - 1)
            del request.session[session_key]
            voto_atual = None
        else:
            if voto_atual == 'like':
                piano.likes = max(0, piano.likes - 1)
            piano.dislikes += 1
            request.session[session_key] = 'dislike'
            voto_atual = 'dislike'

    piano.save()

    # Atualiza destaque automaticamente (top 3 com mais likes)
    top_ids = list(
        Piano.objects.filter(aprovado=True)
        .order_by('-likes')[:3]
        .values_list('id', flat=True)
    )
    Piano.objects.filter(aprovado=True).update(destaque=False)
    Piano.objects.filter(id__in=top_ids, likes__gt=0).update(destaque=True)

    return JsonResponse({
        'likes': piano.likes,
        'voto_atual': voto_atual,
    })


@require_POST
def avaliar_piano(request, piano_id):
    piano = get_object_or_404(Piano, id=piano_id, aprovado=True)
    session_key = f'estrelas_piano_{piano_id}'

    # Só permite uma avaliação por sessão
    if request.session.get(session_key):
        return JsonResponse({'erro': 'Você já avaliou este piano.'}, status=400)

    try:
        estrelas = int(request.POST.get('estrelas', 0))
        if not 1 <= estrelas <= 5:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'erro': 'Avaliação inválida.'}, status=400)

    total = piano.total_avaliacoes
    media = piano.estrelas
    nova_media = ((media * total) + estrelas) / (total + 1)

    piano.estrelas = round(nova_media, 2)
    piano.total_avaliacoes = total + 1
    piano.save()

    request.session[session_key] = estrelas

    return JsonResponse({
        'estrelas': piano.estrelas,
        'total_avaliacoes': piano.total_avaliacoes,
        'minha_avaliacao': estrelas,
    })