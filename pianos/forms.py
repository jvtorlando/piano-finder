from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from urllib.parse import urlsplit

from .models import Piano, Comentario


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
                'autocomplete': 'new-password',
                'placeholder': 'Ex: Livraria Cultura',
            }),
            'endereco': forms.TextInput(attrs={
                'autocomplete': 'new-password',
                'placeholder': 'Ex: Av. Paulista, 2073',
            }),
            'cidade': forms.TextInput(attrs={
                'autocomplete': 'new-password',
                'placeholder': 'Ex: São Paulo',
            }),
            'estado': forms.TextInput(attrs={
                'autocomplete': 'new-password',
                'placeholder': 'Ex: SP',
                'maxlength': '2',
            }),
            'descricao': forms.Textarea(attrs={
                'rows': 3,
                'autocomplete': 'new-password',
                'placeholder': 'Conte algo sobre este piano — horário de acesso, condições, etc. (opcional)',
            }),
            'tipo': forms.HiddenInput(attrs={'id': 'tipoFinal'}),
        }

    def clean_estado(self):
        estado = self.cleaned_data['estado'].strip().upper()
        estados_validos = {
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO',
            'MA', 'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI',
            'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
        }
        if estado not in estados_validos:
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
