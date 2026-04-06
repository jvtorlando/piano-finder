from django import forms
from .models import Piano

class PianoAdminForm(forms.ModelForm):
    upload_foto = forms.ImageField(required=False, label='Enviar nova foto')

    class Meta:
        model = Piano
        fields = '__all__'