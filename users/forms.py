from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import CustomUser, Skill, CompletedJobGallery

# Custom Registration Form
class CustomUserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Choose a username'})
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Create a password'})
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )
    
    # Filter out "Admin" from role choices
    role = forms.ChoiceField(
        choices=[(key, value) for key, value in CustomUser.ROLE_CHOICES if key != 'admin'],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'role']
        
        
        
# Custom Profile Update Form
class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'})
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your first name'}),
        required=True
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your last name'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    contact_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter contact number'})
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Write something about yourself...', 'rows': 3})
    )
    address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your address'})
    )
    gender = forms.ChoiceField(
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = CustomUser
        fields = [
            'profile_picture',
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'bio',
            'address',
            'gender'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
        return user

# Skill Verification Form
class SkillVerificationForm(forms.ModelForm):
    skill_name = forms.CharField(
        label='Skill Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your skill, e.g. Driving',
            'id': 'id_skill_name'
        })
    )
    description = forms.CharField(
        label='Description',
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Brief description',
            'id': 'id_description'
        })
    )
    proof = forms.FileField(
        label='Upload Proof',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'id': 'id_proof'
        })
    )

    class Meta:
        model = Skill
        fields = ['skill_name', 'description', 'proof']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your skill, e.g. Driving'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Brief description'}),
            'proof': forms.FileInput(attrs={'class': 'form-control'}),
        }

# Completed Job Gallery Form
class CompletedJobGalleryForm(forms.ModelForm):
    class Meta:
        model = CompletedJobGallery
        fields = ['image', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Enter a description...'
            }),
        }

# User Location Form
class UserLocationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['location']
        widgets = {
            'location': forms.HiddenInput(attrs={'id': 'id_location'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.location:
            # Set the initial value using the WKT representation
            self.fields['location'].initial = self.instance.location.wkt

# Identity Verification Form
class IdentityVerificationForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['identity_document']
        widgets = {
            # Optionally use ClearableFileInput or custom widget
            'identity_document': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
