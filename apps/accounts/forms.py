from django import forms
from .models import UserProfile, InstructorCertificate, CustomUser

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 4, 'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm'}),
        }

class CustomUserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'no_telp']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm'}),
            'no_telp': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm'}),
        }

class InstructorCertificateForm(forms.ModelForm):
    class Meta:
        model = InstructorCertificate
        fields = ['title', 'issuing_organization', 'issue_date', 'certificate_file']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm', 'placeholder': 'Contoh: AWS Certified Solutions Architect'}),
            'issuing_organization': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm', 'placeholder': 'Contoh: Amazon Web Services'}),
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm'}),
            'certificate_file': forms.FileInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-navy-100 focus:ring-2 focus:ring-navy-900 focus:border-transparent outline-none transition-all text-sm'}),
        }
