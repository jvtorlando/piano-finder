import logging

import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.contrib import admin
from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect
from django.utils.html import format_html

from .models import Piano, Comentario
from .forms_admin import PianoAdminForm


logger = logging.getLogger(__name__)


class PianoAdmin(admin.ModelAdmin):
    form = PianoAdminForm

    class Media:
        css = {
            'all': ('pianos/image-cropper.css',),
        }
        js = (
            'pianos/image-cropper.js',
            'pianos/admin-image-crop.js',
        )

    list_display = (
        'nome_local', 'cidade', 'estado', 'tipo', 'aprovado',
        'esta_funcionando', 'destaque', 'likes', 'data_cadastro', 'thumb',
    )
    list_filter = ('aprovado', 'estado', 'tipo', 'esta_funcionando', 'destaque')
    list_editable = ('aprovado',)
    search_fields = ('nome_local', 'cidade', 'endereco')
    actions = ['aprovar_pianos', 'reprovar_pianos', 'deletar_pianos']
    readonly_fields = (
        'foto_url', 'foto_url_2', 'foto_url_3', 'preview_fotos',
        'likes', 'dislikes', 'estrelas', 'total_avaliacoes', 'data_cadastro',
    )

    fieldsets = (
        ('Informações', {
            'fields': ('nome_local', 'endereco', 'cidade', 'estado', 'tipo', 'descricao')
        }),
        ('Publicação', {
            'fields': ('esta_funcionando', 'aprovado', 'destaque', 'ordem', 'data_cadastro')
        }),
        ('Fotos', {
            'fields': ('upload_foto', 'foto_url', 'foto_url_2', 'foto_url_3', 'preview_fotos')
        }),
        ('Avaliações', {
            'fields': ('likes', 'dislikes', 'estrelas', 'total_avaliacoes')
        }),
    )

    def thumb(self, obj):
        if obj.foto_url:
            return format_html('<img src="{}" style="width:60px;height:40px;object-fit:cover;border-radius:4px;">', obj.foto_url)
        return '—'
    thumb.short_description = 'Foto'

    def preview_fotos(self, obj):
        if obj.fotos:
            imagens = ''.join(
                '<img src="{}" style="width:180px;height:120px;object-fit:cover;border-radius:6px;margin:0 8px 8px 0;">'
                for _ in obj.fotos
            )
            return format_html(imagens, *obj.fotos)
        return '—'
    preview_fotos.short_description = 'Preview'

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

    def aprovar_pianos(self, request, queryset):
        queryset.update(aprovado=True)
        self.message_user(request, f'{queryset.count()} piano(s) aprovado(s).')
    aprovar_pianos.short_description = '✅ Aprovar selecionados'

    def reprovar_pianos(self, request, queryset):
        queryset.update(aprovado=False)
        self.message_user(request, f'{queryset.count()} piano(s) reprovado(s).')
    reprovar_pianos.short_description = '⏸ Reprovar selecionados'

    def deletar_pianos(self, request, queryset):
        total = queryset.count()
        queryset.delete()
        self.message_user(request, f'{total} piano(s) deletado(s) permanentemente.')
    deletar_pianos.short_description = '🗑 Deletar selecionados'


class ComentarioAdmin(admin.ModelAdmin):
    list_display = ('piano', 'nome', 'texto_curto', 'aprovado', 'data')
    list_filter = ('aprovado', 'piano')
    list_editable = ('aprovado',)
    search_fields = ('nome', 'texto', 'piano__nome_local')
    actions = ['aprovar_comentarios', 'reprovar_comentarios']

    def texto_curto(self, obj):
        return obj.texto[:60] + '...' if len(obj.texto) > 60 else obj.texto
    texto_curto.short_description = 'Comentário'

    def aprovar_comentarios(self, request, queryset):
        queryset.update(aprovado=True)
        self.message_user(request, f'{queryset.count()} comentário(s) aprovado(s).')
    aprovar_comentarios.short_description = '✅ Aprovar selecionados'

    def reprovar_comentarios(self, request, queryset):
        queryset.update(aprovado=False)
        self.message_user(request, f'{queryset.count()} comentário(s) reprovado(s).')
    reprovar_comentarios.short_description = '⏸ Reprovar selecionados'


admin.site.register(Piano, PianoAdmin)
admin.site.register(Comentario, ComentarioAdmin)
