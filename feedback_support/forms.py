from django import forms
from .models import Feedback, Category, Policy, NetworkProvider


class FeedbackForm(forms.ModelForm):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Category",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    policy_name = forms.ModelChoiceField(
        queryset=Policy.objects.all(),
        empty_label="Select Policy",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    network_provider = forms.ModelChoiceField(
        queryset=NetworkProvider.objects.all(),
        empty_label="Select Network Provider",
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Feedback
        fields = ['category', 'policy_name', 'network_provider', 'description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Describe your feedback...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].required = True


class FeedbackEditForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ['description']
        widgets = {
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6
            }),
        }