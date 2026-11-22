from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from urllib.parse import urlsplit

from .models import UFS, Comentario, Piano


class PianoForm(forms.ModelForm):
    foto_url_1 = forms.URLField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'foto_url_1'}),
    )
    foto_url_2 = forms.URLField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'foto_url_2'}),
    )
    foto_url_3 = forms.URLField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'foto_url_3'}),
    )

    class Meta:
        model = Piano
        fields = [
            'nome_local',
            'endereco',
            'cidade',
            'estado',
            'esta_funcionando',
            'descricao',
            'tipo',
        ]
        widgets = {
            'nome_local': forms.TextInput(attrs={
                'class': 'field-input',
                'autocomplete': 'new-password',
                'placeholder': 'Ex: Livraria Cultura',
            }),
            'endereco': forms.TextInput(attrs={
                'class': 'field-input',
                'autocomplete': 'new-password',
                'placeholder': 'Ex: Av. Paulista, 2073',
            }),
            'cidade': forms.TextInput(attrs={
                'class': 'field-input',
                'autocomplete': 'new-password',
                'placeholder': 'Ex: São Paulo',
            }),
            'estado': forms.TextInput(attrs={
                'class': 'field-input uppercase',
                'autocomplete': 'new-password',
                'placeholder': 'Ex: SP',
                'maxlength': '2',
            }),
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'class': 'field-input min-h-28 resize-y',
                'autocomplete': 'new-password',
                'placeholder': 'Horário em que dá para tocar, andar, se precisa pedir na recepção...',
            }),
            'tipo': forms.RadioSelect,
            'esta_funcionando': forms.CheckboxInput(attrs={
                'class': 'size-5 shrink-0 cursor-pointer accent-gold',
            }),
        }

    def clean_estado(self):
        estado = self.cleaned_data['estado'].strip().upper()
        if estado not in UFS:
            raise ValidationError('Informe uma UF brasileira válida, como SP ou RJ.')
        return estado

    def _clean_cloudinary_url(self, field_name):
        url = self.cleaned_data.get(field_name)
        if not url:
            return url

        cloud_name = settings.CLOUDINARY_STORAGE.get('CLOUD_NAME')
        parsed = urlsplit(url)
        expected_prefix = f'/{cloud_name}/image/upload/' if cloud_name else None
        is_valid = (
            parsed.scheme == 'https'
            and parsed.hostname == 'res.cloudinary.com'
            and expected_prefix
            and parsed.path.startswith(expected_prefix)
        )
        if not is_valid:
            raise ValidationError('A foto enviada não pertence ao Cloudinary do Piano Finder.')
        return url

    def clean_foto_url_1(self):
        return self._clean_cloudinary_url('foto_url_1')

    def clean_foto_url_2(self):
        return self._clean_cloudinary_url('foto_url_2')

    def clean_foto_url_3(self):
        return self._clean_cloudinary_url('foto_url_3')


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['nome', 'texto']
        widgets = {
            'nome': forms.TextInput(attrs={
                'placeholder': 'Seu nome (opcional)',
                'autocomplete': 'new-password',
            }),
            'texto': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Escreva seu comentário...',
                'autocomplete': 'new-password',
            }),
        }
