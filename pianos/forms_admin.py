from django import forms
from django.core.exceptions import ValidationError
from unfold.widgets import UnfoldAdminImageFieldWidget

from .models import Piano


MAX_IMAGE_SIZE = 10 * 1024 * 1024


class PianoAdminForm(forms.ModelForm):
    upload_foto = forms.ImageField(
        required=False,
        label='Enviar nova foto',
        help_text=(
            'Antes do envio, ajuste a foto no formato 16:10. '
            'Imagem JPG, PNG, WEBP ou GIF com até 10 MB; o resultado será convertido em JPG.'
        ),
        widget=UnfoldAdminImageFieldWidget(attrs={
            'accept': 'image/*',
            'data-piano-image-cropper': 'true',
        }),
    )

    class Meta:
        model = Piano
        fields = '__all__'

    def clean_upload_foto(self):
        foto = self.cleaned_data.get('upload_foto')
        if foto and foto.size > MAX_IMAGE_SIZE:
            raise ValidationError('A imagem deve ter no máximo 10 MB.')
        return foto
