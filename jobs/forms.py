from django import forms
from .models import Job, JobApplication, Contract, ProgressLog
from django.forms.widgets import ClearableFileInput

class MultipleFileInput(ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result

class JobForm(forms.ModelForm):
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
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'street'})
    )
    house_number = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'house_number'})
    )

    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    job_picture = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Job
        fields = [
            'title', 'description', 'category', 'budget',
            'municipality', 'barangay', 'subdivision', 'street', 'house_number',
            'latitude', 'longitude', 'job_picture',
            'tasks', 'duration', 'schedule', 'start_datetime',
            'tools_provided', 'materials_provided', 'required_skills',
            'payment_method', 'payment_schedule', 'urgency', 'number_of_workers'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }

# NOT a ModelForm — plain Form to support multiple files
class JobImageForm(forms.Form):
    images = MultipleFileField(required=False)

class JobApplicationForm(forms.ModelForm):
    class Meta:
        model = JobApplication
        fields = [
            'cover_letter',
            'proposed_rate',
            'available_start_date',
            'expected_duration',
            'experience',
            'Other_link',
            'certifications',
            'additional_notes',
        ]
        widgets = {
            'cover_letter': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'proposed_rate': forms.TextInput(attrs={'class': 'form-control'}),
            'available_start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expected_duration': forms.TextInput(attrs={'class': 'form-control'}),
            'experience': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'Other_link': forms.URLInput(attrs={'class': 'form-control'}),
            'certifications': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'additional_notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ContractForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'status', 
            'payment_status',
            'is_revision_requested',
            'feedback_by_client',
            'rating_by_client',
            'feedback_by_worker',
            'start_date',
            'end_date',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'feedback_by_client': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'feedback_by_worker': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'rating_by_client': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class ProgressLogForm(forms.ModelForm):
    class Meta:
        model = ProgressLog
        fields = ['status', 'message']
        widgets = {
            'status': forms.TextInput(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class ContractDraftForm(forms.ModelForm):
    class Meta:
        model = Contract
        fields = [
            'scope_of_work',
            'payment_terms',
            'deliverables',
            'start_date',
            'end_date',
        ]
        widgets = {
            'scope_of_work': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'payment_terms': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'deliverables': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        }
