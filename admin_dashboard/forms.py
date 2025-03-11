from django import forms
from .models import ModeratedWord

class ModeratedWordForm(forms.ModelForm):
    class Meta:
        model = ModeratedWord
        fields = ['word']
        widgets = {
            'word': forms.TextInput(attrs={'class': 'form-control'}),
        }
