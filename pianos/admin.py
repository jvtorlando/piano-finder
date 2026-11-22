import logging

import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import ChoicesDropdownFilter
from unfold.decorators import action, display
from unfold.enums import ActionVariant
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .forms_admin import PianoAdminForm
from .geocoding import geocodificar
from .models import Comentario, Piano


logger = logging.getLogger(__name__)

CAMPOS_DE_ENDERECO = {'nome_local', 'endereco', 'cidade', 'estado'}
LIMITE_GEOCODIFICACAO_EM_LOTE = 8

admin.site.index_template = 'admin/pianos_dashboard.html'
admin.site.index_title = 'Painel'


class ComentarioInline(TabularInline):
    model = Comentario
    extra = 0
    tab = True
    verbose_name_plural = 'Comentários'
    fields = ('nome', 'texto', 'aprovado', 'data')
    readonly_fields = ('data',)


@admin.register(Piano)
class PianoAdmin(ModelAdmin):
    form = PianoAdminForm
    inlines = [ComentarioInline]

    class Media:
        css = {
            'all': ('pianos/image-cropper.css',),
        }
        js = (
            'pianos/image-cropper.js',
            'pianos/admin-image-crop.js',
        )

    list_display = (
        'thumb', 'local', 'status', 'tipo_label', 'esta_funcionando',
        'no_mapa', 'destaque', 'likes', 'nota', 'enviado',
    )
    list_display_links = ('thumb', 'local')
    list_filter = (
        'aprovado',
        ('tipo', ChoicesDropdownFilter),
        'estado',
        'esta_funcionando',
        'destaque',
    )
    list_filter_submit = True
    list_per_page = 25
    search_fields = ('nome_local', 'cidade', 'endereco')
    ordering = ('aprovado', '-data_cadastro')
    date_hierarchy = 'data_cadastro'
    warn_unsaved_form = True
    actions = ['aprovar_pianos', 'reprovar_pianos', 'buscar_coordenadas']
    actions_detail = ['aprovar_este', 'ver_no_site']
    readonly_fields = (
        'foto_url', 'foto_url_2', 'foto_url_3', 'preview_fotos', 'mapa_link',
        'likes', 'dislikes', 'estrelas', 'total_avaliacoes', 'data_cadastro',
    )

    fieldsets = (
        ('Informações', {
            'classes': ['tab'],
            'fields': ('nome_local', 'endereco', ('cidade', 'estado'), 'tipo', 'descricao'),
        }),
        ('Fotos', {
            'classes': ['tab'],
            'fields': ('preview_fotos', 'upload_foto', 'foto_url', 'foto_url_2', 'foto_url_3'),
        }),
        ('Localização', {
            'classes': ['tab'],
            'description': (
                'As coordenadas são buscadas automaticamente pelo endereço quando o piano é salvo. '
                'Se o ponto ficar errado, corrija os números aqui (ex.: copiando do Google Maps).'
            ),
            'fields': (('latitude', 'longitude'), 'mapa_link'),
        }),
        ('Publicação', {
            'classes': ['tab'],
            'fields': ('aprovado', 'esta_funcionando', 'destaque', 'ordem', 'data_cadastro'),
        }),
        ('Avaliações', {
            'classes': ['tab'],
            'fields': (('likes', 'dislikes'), ('estrelas', 'total_avaliacoes')),
        }),
    )

    # ── Colunas da lista ────────────────────────────────────────────────────

    @display(description='Foto')
    def thumb(self, obj):
        if obj.foto_url:
            return format_html(
                '<img src="{}" alt="" style="width:80px;min-width:80px;height:50px;object-fit:cover;border-radius:6px;display:block">',
                obj.foto_url,
            )
        return mark_safe(
            '<span class="material-symbols-outlined" style="width:80px;height:50px;display:flex;align-items:center;'
            'justify-content:center;border-radius:6px;background:var(--color-base-800);color:var(--color-base-500)">image</span>'
        )

    @display(description='No mapa', boolean=True)
    def no_mapa(self, obj):
        return obj.tem_coordenadas

    @display(description='Conferir no mapa')
    def mapa_link(self, obj):
        if not obj.tem_coordenadas:
            return 'Sem coordenadas ainda.'
        return format_html(
            '<a href="https://www.openstreetmap.org/?mlat={0}&amp;mlon={1}#map=18/{0}/{1}" '
            'target="_blank" rel="noopener" class="text-primary-600 underline">Abrir no OpenStreetMap ↗</a>',
            obj.latitude, obj.longitude,
        )

    @display(description='Enviado', ordering='data_cadastro')
    def enviado(self, obj):
        return localtime(obj.data_cadastro).strftime('%d/%m/%Y')

    @display(description='Local', header=True, ordering='nome_local')
    def local(self, obj):
        return obj.nome_local, f'{obj.cidade}/{obj.estado}'

    @display(
        description='Status',
        ordering='aprovado',
        label={'Publicado': 'success', 'Pendente': 'warning'},
    )
    def status(self, obj):
        return 'Publicado' if obj.aprovado else 'Pendente'

    @display(description='Tipo', ordering='tipo', label=True)
    def tipo_label(self, obj):
        return obj.get_tipo_display()

    @display(description='Nota', ordering='estrelas')
    def nota(self, obj):
        if not obj.total_avaliacoes:
            return '—'
        return f'★ {obj.estrelas:.1f} ({obj.total_avaliacoes})'

    @display(description='Fotos atuais')
    def preview_fotos(self, obj):
        if not obj.fotos:
            return '—'
        return format_html_join(
            '',
            '<img src="{}" alt="" style="width:200px;aspect-ratio:16/10;object-fit:cover;border-radius:8px;margin:0 8px 8px 0">',
            ((foto,) for foto in obj.fotos),
        )

    # ── Ações ───────────────────────────────────────────────────────────────

    @action(description='Aprovar selecionados', icon='check_circle')
    def aprovar_pianos(self, request, queryset):
        total = queryset.update(aprovado=True)
        self.message_user(request, f'{total} piano(s) aprovado(s).', messages.SUCCESS)

    @action(description='Buscar coordenadas no mapa', icon='location_on')
    def buscar_coordenadas(self, request, queryset):
        sem_coordenadas = list(
            queryset.filter(latitude__isnull=True)[:LIMITE_GEOCODIFICACAO_EM_LOTE]
        )
        encontrados, falhas = 0, []
        for piano in sem_coordenadas:
            if self._geocodificar(piano):
                piano.save(update_fields=['latitude', 'longitude'])
                encontrados += 1
            else:
                falhas.append(piano.nome_local)

        if encontrados:
            self.message_user(request, f'Coordenadas encontradas para {encontrados} piano(s).', messages.SUCCESS)
        if falhas:
            self.message_user(
                request,
                'Não encontrei o endereço de: ' + ', '.join(falhas) + '. Preencha latitude e longitude manualmente.',
                messages.WARNING,
            )
        restantes = queryset.filter(latitude__isnull=True).count() - len(falhas)
        if restantes > 0:
            self.message_user(
                request,
                f'Ainda faltam {restantes}. Rode a ação de novo (são buscados {LIMITE_GEOCODIFICACAO_EM_LOTE} por vez).',
                messages.INFO,
            )
        if not sem_coordenadas:
            self.message_user(request, 'Todos os pianos selecionados já têm coordenadas.')

    def _geocodificar(self, piano):
        coordenadas = geocodificar(piano)
        if coordenadas:
            piano.latitude, piano.longitude = coordenadas
            return True
        return False

    @action(description='Voltar para pendente', icon='pause_circle')
    def reprovar_pianos(self, request, queryset):
        total = queryset.update(aprovado=False)
        self.message_user(request, f'{total} piano(s) voltaram para pendente.')

    def has_aprovar_este_permission(self, request, object_id=None):
        # O botão "Aprovar e publicar" só aparece em pianos ainda pendentes.
        if not self.has_change_permission(request):
            return False
        if object_id is None:
            return True
        return Piano.objects.filter(pk=object_id, aprovado=False).exists()

    @action(
        description='Aprovar e publicar',
        icon='check_circle',
        variant=ActionVariant.PRIMARY,
        permissions=['aprovar_este'],
        # A janela de confirmação envia um POST com CSRF; um simples GET não altera nada.
        dialog={
            'title': 'Aprovar e publicar este piano?',
            'description': 'Ele passa a aparecer no catálogo público do Piano Finder.',
            'form_submit_text': 'Aprovar e publicar',
        },
    )
    def aprovar_este(self, request, form, object_id):
        piano = Piano.objects.get(pk=object_id)
        piano.aprovado = True
        if not piano.tem_coordenadas:
            self._geocodificar(piano)
        piano.save(update_fields=['aprovado', 'latitude', 'longitude'])
        self.message_user(request, 'Piano aprovado e publicado no site.', messages.SUCCESS)
        destino = reverse('admin:pianos_piano_change', args=[object_id])
        if request.headers.get('HX-Request'):
            # A confirmação é enviada via HTMX; este cabeçalho faz a página inteira navegar.
            resposta = HttpResponse(status=204)
            resposta['HX-Redirect'] = destino
            return resposta
        return redirect(destino)

    @action(description='Ver no site', icon='open_in_new')
    def ver_no_site(self, request, object_id):
        piano = Piano.objects.get(pk=object_id)
        if not piano.aprovado:
            self.message_user(request, 'Este piano ainda não está publicado.', messages.WARNING)
            return redirect(reverse('admin:pianos_piano_change', args=[object_id]))
        return redirect(reverse('detalhe_piano', args=[object_id]))

    # ── Upload para o Cloudinary ────────────────────────────────────────────

    def save_model(self, request, obj, form, change):
        if 'upload_foto' in request.FILES:
            foto = request.FILES['upload_foto']
            resultado = cloudinary.uploader.unsigned_upload(
                foto,
                settings.CLOUDINARY_UPLOAD_PRESET,
                cloud_name=settings.CLOUDINARY_STORAGE['CLOUD_NAME'],
                resource_type='image',
            )
            secure_url = resultado.get('secure_url')
            if not secure_url:
                raise CloudinaryError('Cloudinary response did not include secure_url.')
            obj.foto_url = secure_url

        # Busca as coordenadas se ainda não existem ou se o endereço mudou,
        # a menos que quem editou tenha preenchido latitude/longitude à mão.
        alterados = set(form.changed_data) if form is not None else set()
        editou_coordenadas = bool(alterados & {'latitude', 'longitude'})
        precisa_geocodificar = not obj.tem_coordenadas or bool(alterados & CAMPOS_DE_ENDERECO)
        if precisa_geocodificar and not editou_coordenadas and form is not None:
            if not self._geocodificar(obj):
                self.message_user(
                    request,
                    'Não encontrei este endereço no mapa. Preencha latitude e longitude na aba Localização.',
                    messages.WARNING,
                )
        super().save_model(request, obj, form, change)

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        try:
            return super().changeform_view(request, object_id, form_url, extra_context)
        except CloudinaryError:
            logger.exception('Cloudinary image upload failed in Django Admin.')
            self.message_user(
                request,
                'Não foi possível enviar a imagem. Verifique o arquivo e tente novamente.',
                level=messages.ERROR,
            )
            return redirect(request.path)


@admin.register(Comentario)
class ComentarioAdmin(ModelAdmin):
    list_display = ('texto_curto', 'autor', 'piano', 'status', 'data')
    list_filter = ('aprovado', 'piano')
    list_filter_submit = True
    search_fields = ('nome', 'texto', 'piano__nome_local')
    ordering = ('aprovado', '-data')
    actions = ['aprovar_comentarios', 'reprovar_comentarios']
    autocomplete_fields = ('piano',)

    @display(description='Comentário')
    def texto_curto(self, obj):
        return obj.texto[:80] + '…' if len(obj.texto) > 80 else obj.texto

    @display(description='Autor')
    def autor(self, obj):
        return obj.nome or 'Anônimo'

    @display(
        description='Status',
        ordering='aprovado',
        label={'Publicado': 'success', 'Pendente': 'warning'},
    )
    def status(self, obj):
        return 'Publicado' if obj.aprovado else 'Pendente'

    @action(description='Aprovar selecionados', icon='check_circle')
    def aprovar_comentarios(self, request, queryset):
        total = queryset.update(aprovado=True)
        self.message_user(request, f'{total} comentário(s) aprovado(s).', messages.SUCCESS)

    @action(description='Voltar para pendente', icon='pause_circle')
    def reprovar_comentarios(self, request, queryset):
        total = queryset.update(aprovado=False)
        self.message_user(request, f'{total} comentário(s) voltaram para pendente.')


# Usuários e grupos com o mesmo visual do restante do admin.
admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
