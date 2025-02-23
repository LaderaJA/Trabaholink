from django import forms
from .models import Job, JobApplication

class JobForm(forms.ModelForm):
    """Form for creating and updating job postings."""
    
    municipality = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'municipality-input'})
    )
    barangay = forms.CharField(
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'barangay-input'})
    )
    subdivision = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    street = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    house_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    job_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Job
        fields = [
            'title', 'description', 'category', 'budget',
            'municipality', 'barangay', 'subdivision', 'street', 'house_number',
            'job_picture'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class JobApplicationForm(forms.ModelForm):
    """Form for workers to apply for a job."""
    
    cover_letter = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write your application message...'})
    )

    class Meta:
        model = JobApplication
        fields = ['cover_letter']
