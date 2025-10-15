from django import forms
from .models import ServicePost, ServicePostImage

class ServicePostForm(forms.ModelForm):
    class Meta:
        model = ServicePost
        fields = [
            'headline',
            'description',
            'category',
            'pricing',
            'availability',
            'contact_number',
            'email',
            'address',
        ]
        widgets = {
            'headline': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'placeholder': 'e.g., Professional Plumbing Services'
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'rows': 5,
                'placeholder': 'Describe your service in detail...'
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue'
            }),
            'pricing': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'availability': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'placeholder': 'e.g., Mon-Fri 9AM-5PM'
            }),
            'contact_number': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'placeholder': '09XX XXX XXXX'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'placeholder': 'your.email@example.com'
            }),
            'address': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-trabaholink-blue',
                'placeholder': 'Service location or coverage area'
            }),
        }
        labels = {
            'headline': 'Service Title',
            'description': 'Service Description',
            'category': 'Service Category',
            'pricing': 'Price (₱)',
            'availability': 'Availability',
            'contact_number': 'Contact Number',
            'email': 'Email Address',
            'address': 'Service Location',
        }

class ServiceImageForm(forms.ModelForm):
    class Meta:
        model = ServicePostImage
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none',
                'accept': 'image/*'
            })
        }
