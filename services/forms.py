from django import forms
from .models import ServicePost

class ServicePostForm(forms.ModelForm):
    service_items = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'One service per line, fields separated by |'}),
        required=False,
        help_text="Enter service items in the format: Service Name|Price|Duration|Description"
    )

    class Meta:
        model = ServicePost
        fields = [
            'headline',
            'description',
            'availability',
            'contact_number',
            'email',
            'category',
            'address',
        ]
