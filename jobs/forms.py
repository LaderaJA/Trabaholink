from django import forms
from .models import Job, JobApplication, Contract, ProgressLog, JobOffer, WorkerAvailability
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
            'payment_method', 'payment_schedule', 'urgency', 'number_of_workers',
            'posting_duration_days'
        ]
        # Note: 'vacancies' is auto-managed and set to match 'number_of_workers' on creation
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'category': forms.Select(attrs={'class': 'form-control'}),
            'budget': forms.NumberInput(attrs={'class': 'form-control'}),
            'start_datetime': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'posting_duration_days': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '90',
                'value': '7',
                'help_text': 'Number of days this job posting will be active (1-90 days, default: 7)'
            }),
        }
        labels = {
            'posting_duration_days': 'Posting Duration (Days)',
        }
        help_texts = {
            'posting_duration_days': 'How many days should this job posting remain active? (Default: 7 days)',
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
            'start_time',
            'end_time',
        ]
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'placeholder': '09:00'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'placeholder': '17:00'}),
            'feedback_by_client': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'feedback_by_worker': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'rating_by_client': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        # Validate dates
        if start_date and end_date and end_date < start_date:
            raise forms.ValidationError({
                'end_date': 'End date must be after or equal to start date.'
            })
        
        # Validate times
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError({
                'end_time': 'End time must be after start time.'
            })
        
        # Check worker availability if all date/time fields are provided
        if start_date and end_date and start_time and end_time:
            # Get worker from instance (contract being edited)
            if self.instance and self.instance.worker:
                worker = self.instance.worker
                
                # Check for schedule conflicts with existing contracts
                conflicts = self.instance.check_time_conflict()
                if conflicts:
                    conflict_details = []
                    for conflict in conflicts[:3]:  # Show first 3 conflicts
                        conflict_details.append(
                            f"• {conflict['job_title']} ({conflict['dates']}, {conflict['times']})"
                        )
                    
                    error_msg = "Schedule conflict detected with existing contracts:\n" + "\n".join(conflict_details)
                    if len(conflicts) > 3:
                        error_msg += f"\n...and {len(conflicts) - 3} more conflict(s)"
                    
                    raise forms.ValidationError(error_msg)
                
                # Check worker's availability settings
                availability_check = WorkerAvailability.check_availability_for_contract(
                    worker=worker,
                    start_date=start_date,
                    end_date=end_date,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if not availability_check['available']:
                    conflicts = availability_check['conflicts']
                    conflict_details = []
                    for conflict in conflicts[:5]:  # Show first 5 days
                        conflict_details.append(
                            f"• {conflict['date'].strftime('%a, %b %d')}: {conflict['reason']}"
                        )
                    
                    error_msg = "Worker is not available for the proposed schedule:\n" + "\n".join(conflict_details)
                    if len(conflicts) > 5:
                        error_msg += f"\n...and {len(conflicts) - 5} more day(s) with conflicts"
                    
                    raise forms.ValidationError(error_msg)
        
        return cleaned_data

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
            'start_time',
            'end_time',
        ]
        widgets = {
            'scope_of_work': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 6,
                'maxlength': '2000',
                'placeholder': 'Define the complete scope of work, deliverables, milestones, and exclusions...'
            }),
            'payment_terms': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'maxlength': '1000',
                'placeholder': 'Specify total cost, payment schedule, method, and terms...'
            }),
            'deliverables': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5,
                'maxlength': '1500',
                'placeholder': 'List all items to be delivered, formats, documentation, and support...'
            }),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'start_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'placeholder': '09:00'}),
            'end_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control', 'placeholder': '17:00'}),
        }
        labels = {
            'scope_of_work': 'Scope of Work',
            'payment_terms': 'Payment Terms',
            'deliverables': 'Deliverables',
            'start_date': 'Project Start Date',
            'end_date': 'Project End Date (Deadline)',
            'start_time': 'Daily Start Time',
            'end_time': 'Daily End Time',
        }
        help_texts = {
            'scope_of_work': 'Maximum 2000 characters. Be specific about what work will be performed.',
            'payment_terms': 'Maximum 1000 characters. Include total amount and payment schedule.',
            'deliverables': 'Maximum 1500 characters. List everything the client will receive.',
            'start_date': 'When will the work begin?',
            'end_date': 'When should the project be completed?',
            'start_time': 'Daily work start time (e.g., 9:00 AM)',
            'end_time': 'Daily work end time (e.g., 5:00 PM)',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        scope_of_work = cleaned_data.get('scope_of_work')
        payment_terms = cleaned_data.get('payment_terms')
        
        # Validate dates
        if start_date and end_date:
            if end_date <= start_date:
                raise forms.ValidationError({
                    'end_date': 'End date must be after the start date.'
                })
        
        # Validate times
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError({
                'end_time': 'End time must be after start time.'
            })
        
        # Validate required fields have meaningful content
        if scope_of_work and len(scope_of_work.strip()) < 50:
            raise forms.ValidationError({
                'scope_of_work': 'Scope of work must be at least 50 characters. Please provide more details.'
            })
        
        if payment_terms and len(payment_terms.strip()) < 20:
            raise forms.ValidationError({
                'payment_terms': 'Payment terms must be at least 20 characters. Please provide more details.'
            })
        
        # Check worker availability if all date/time fields are provided
        if start_date and end_date and start_time and end_time:
            # Get worker from instance (contract being drafted)
            if self.instance and self.instance.worker:
                worker = self.instance.worker
                
                # Check for schedule conflicts with existing contracts
                conflicts = self.instance.check_time_conflict()
                if conflicts:
                    conflict_details = []
                    for conflict in conflicts[:3]:  # Show first 3 conflicts
                        conflict_details.append(
                            f"• {conflict['job_title']} ({conflict['dates']}, {conflict['times']})"
                        )
                    
                    error_msg = "⚠️ Schedule conflict with existing contracts:\n" + "\n".join(conflict_details)
                    if len(conflicts) > 3:
                        error_msg += f"\n...and {len(conflicts) - 3} more conflict(s)"
                    
                    raise forms.ValidationError(error_msg)
                
                # Check worker's availability settings
                availability_check = WorkerAvailability.check_availability_for_contract(
                    worker=worker,
                    start_date=start_date,
                    end_date=end_date,
                    start_time=start_time,
                    end_time=end_time
                )
                
                if not availability_check['available']:
                    conflicts = availability_check['conflicts']
                    conflict_details = []
                    for conflict in conflicts[:5]:  # Show first 5 days
                        conflict_details.append(
                            f"• {conflict['date'].strftime('%a, %b %d')}: {conflict['reason']}"
                        )
                    
                    error_msg = "⚠️ Worker is not available for the proposed schedule:\n" + "\n".join(conflict_details)
                    if len(conflicts) > 5:
                        error_msg += f"\n...and {len(conflicts) - 5} more day(s) with conflicts"
                    error_msg += "\n\n💡 Tip: Adjust the schedule or contact the worker to update their availability."
                    
                    raise forms.ValidationError(error_msg)
        
        return cleaned_data


class JobOfferForm(forms.ModelForm):
    """Form for creating job offers"""
    class Meta:
        model = JobOffer
        fields = [
            'offered_rate',
            'proposed_start_date',
            'proposed_end_date',
            'work_schedule',
            'message',
            'terms_and_conditions',
        ]
        widgets = {
            'offered_rate': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'proposed_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'proposed_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'work_schedule': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., M-F, 9AM-5PM'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Write a message to the worker...'}),
            'terms_and_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Specific terms for this offer (optional)'}),
        }
        labels = {
            'offered_rate': 'Offered Rate (₱)',
            'proposed_start_date': 'Start Date',
            'proposed_end_date': 'End Date (Optional)',
            'work_schedule': 'Work Schedule',
            'message': 'Message to Worker',
            'terms_and_conditions': 'Terms and Conditions',
        }
