from django import forms
from .models import Piano, Comentario

class PianoForm(forms.ModelForm):
    foto   = forms.ImageField(required=False, label='Foto principal')
    foto_2 = forms.ImageField(required=False, label='Foto 2 (opcional)')
    foto_3 = forms.ImageField(required=False, label='Foto 3 (opcional)')

    class Meta:
        model = Piano
        fields = ['nome_local', 'endereco', 'cidade', 'estado', 'esta_funcionando', 'descricao']
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
        }


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