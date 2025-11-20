from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import ModeratedWord

User = get_user_model()


class ModeratedWordForm(forms.ModelForm):
    class Meta:
        model = ModeratedWord
        fields = ['word', 'is_banned']
        widgets = {
            'word': forms.TextInput(attrs={'class': 'form-control'}),
            'is_banned': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AdminCreationForm(UserCreationForm):
    """Form for creating admin users"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'admin@trabaholink.com'
        })
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    is_superuser = forms.BooleanField(
        required=False,
        initial=False,
        label='Superuser (Full admin access)',
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        help_text='Superusers have all permissions and can manage other admins.'
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'password1', 'password2', 'is_superuser')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Password'})
        self.fields['password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Confirm Password'})

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.is_staff = True  # All admins are staff
        user.is_superuser = self.cleaned_data.get('is_superuser', False)
        user.role = 'client'  # Default role
        user.is_active = True
        
        if commit:
            user.save()
        return user
