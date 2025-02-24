from django import forms
from .models import Message
from django.contrib.auth import get_user_model


class MessageForm(forms.ModelForm):
    """Form for sending messages."""
    
    content = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Type a message..."})
    )

    class Meta:
        model = Message
        fields = ["content"]


User = get_user_model()

class StartConversationForm(forms.Form):
    username = forms.CharField(
        label="Enter the username",
        max_length=150,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Username"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"]
        if not User.objects.filter(username=username).exists():
            raise forms.ValidationError("User not found.")
        return username
