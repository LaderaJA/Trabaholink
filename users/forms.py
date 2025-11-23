from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone
from .models import CustomUser, Skill, CompletedJobGallery, AccountVerification, VALID_ID_CHOICES
from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model

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


# Social Account Signup Form
class SocialSignupForm(forms.Form):
    """Form for social account users to select their role"""
    role = forms.ChoiceField(
        choices=[(key, value) for key, value in CustomUser.ROLE_CHOICES if key != 'admin'],
        widget=forms.RadioSelect(attrs={'class': 'role-radio'}),
        label='I want to join as:'
    )
    
    def __init__(self, *args, **kwargs):
        # Accept and ignore the sociallogin parameter that allauth passes
        self.sociallogin = kwargs.pop('sociallogin', None)
        super().__init__(*args, **kwargs)
    
    def try_save(self, request):
        """
        Required by allauth to create and save the user.
        Returns tuple (user, is_new) where is_new indicates if user was created.
        """
        # Check if this is a new user or existing
        is_new = not self.sociallogin.user.pk
        
        # Let the adapter create the user with the form data
        # The adapter will handle setting the role from the form
        from allauth.socialaccount.adapter import get_adapter
        adapter = get_adapter()
        user = adapter.save_user(request, self.sociallogin, form=self)
        
        # Return tuple (user, is_new) as expected by allauth
        return (user, is_new)
    
    def signup(self, request, user):
        """Called by allauth after user is created (if needed)"""
        # Role is already set in try_save, but keep this for compatibility
        pass


class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        UserModel = get_user_model()
        email_field = UserModel.get_email_field_name()
        users = UserModel._default_manager.filter(**{f"{email_field}__iexact": email}, is_active=True)
        users = list(users)
        print(f"[PWD RESET] get_users count={len(users)} for email={email}")
        for u in users:
            print(f"[PWD RESET] candidate id={u.pk} username={u.username} usable={u.has_usable_password()}")
            yield u
        
        
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
    job_title = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Software Developer, Electrician, Plumber'})
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
    cover_photo = forms.ChoiceField(
        choices=[
            ('default1', 'Purple Gradient'),
            ('default2', 'Pink Gradient'),
            ('default3', 'Blue Gradient'),
            ('default4', 'Green Gradient'),
            ('default5', 'Sunset Gradient'),
            ('default6', 'Ocean Gradient'),
        ],
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'cover-photo-choice'})
    )
    cover_photo_custom = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )
    cv_file = forms.FileField(
        required=False,
        label='CV/Resume',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'id': 'id_cv_file'
        }),
        help_text='Upload your CV/Resume (PDF, DOC, or DOCX format, max 5MB)'
    )

    class Meta:
        model = CustomUser
        fields = [
            'profile_picture',
            'cover_photo',
            'cover_photo_custom',
            'username',
            'first_name',
            'last_name',
            'email',
            'contact_number',
            'bio',
            'job_title',
            'address',
            'gender',
            'cv_file'
        ]

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Update CV upload timestamp if a new CV file was uploaded
        if self.cleaned_data.get('cv_file'):
            user.cv_uploaded_at = timezone.now()
        
        if commit:
            user.save()
        return user

# Skill Verification Form
class SkillVerificationForm(forms.ModelForm):
    name = forms.CharField(
        label='Skill Name',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your skill, e.g. Driving',
            'id': 'id_name'
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
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'id': 'id_proof'
        })
    )

    class Meta:
        model = Skill
        fields = ['name', 'description', 'proof']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make proof field not required if we're updating an existing skill
        if self.instance and self.instance.pk:
            self.fields['proof'].required = False

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


# eKYC Verification Forms
class VerificationStep1Form(forms.Form):
    """Personal Information Step"""
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your full name as it appears on your ID'
        })
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Enter your complete address'
        })
    )
    contact_number = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. 09123456789'
        })
    )
    gender = forms.ChoiceField(
        choices=[('', 'Select Gender')] + list(CustomUser._meta.get_field('gender').choices),
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class VerificationStep2Form(forms.Form):
    """ID Upload Step"""
    id_type = forms.ChoiceField(
        choices=[('', 'Select ID Type')] + list(VALID_ID_CHOICES),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    id_image_front = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
    id_image_back = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )


class VerificationStep3Form(forms.Form):
    """Selfie Verification Step"""
    selfie_image = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        })
    )
