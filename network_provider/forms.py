from django import forms
from policy.models import Policy
from .utils import get_policy_coverage_amount, convert_to_int
from .models import NetworkProvider


class EligibilityCheckForm(forms.Form):
    policy_name = forms.ChoiceField(
        label="Policy Name",
        required=True,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'policy_name'
        })
    )

    coverage_type = forms.ChoiceField(
        label="Coverage Type",
        required=True,
        choices=[
            ('', '-- Select coverage type --'),
            ('Medical & Hospitalization', 'Medical & Hospitalization'),
            ('Accident Cover', 'Accident Cover'),
            ('Critical Illness', 'Critical Illness'),
            ('Maternity', 'Maternity'),
            ('OPD', 'OPD (Outpatient Department)'),
            ('Dental', 'Dental Coverage'),
            ('Vision', 'Vision Care'),
            ('Comprehensive', 'Comprehensive'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'coverage_type'
        })
    )

    coverage_limit = forms.IntegerField(
        label="Coverage Limit",
        required=True,
        min_value=1000,
        max_value=10000000,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'id': 'coverage_limit',
            'placeholder': 'e.g., 500000',
            'min': '1000',
            'max': '10000000',
            'step': '1000'
        })
    )

    validity_years = forms.ChoiceField(
        label="Validity Period",
        required=True,
        choices=[
            ('', '-- Select validity period --'),
            ('1', '1 Year'),
            ('2', '2 Years'),
            ('3', '3 Years'),
            ('4', '4 Years'),
            ('5', '5 Years'),
            ('6', '6 Years'),
            ('7', '7 Years'),
            ('8', '8 Years'),
            ('9', '9 Years'),
            ('10', '10 Years'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'validity_years'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.load_policy_choices()

    def load_policy_choices(self):
        """Load policy choices from database"""
        try:
            # Get active policies
            policies = Policy.objects.filter(is_active=True)

            # Create choices list
            policy_choices = [('', '-- Select your policy --')]

            for policy in policies:
                # Use policy_id as the value
                policy_value = policy.policy_id

                # Get coverage amount for display
                coverage_raw = getattr(policy, 'coverage_limit', '0')
                coverage_int = convert_to_int(coverage_raw)

                # Format for display - show original string and converted value
                if 'LAKH' in coverage_raw.upper() or 'L' in coverage_raw.upper():
                    display_raw = coverage_raw
                else:
                    display_raw = f"₹{coverage_int:,}"

                policy_display = f"{policy.name} ({display_raw})"

                policy_choices.append((policy_value, policy_display))

            # Update the choices for the field
            self.fields['policy_name'].choices = policy_choices

        except Exception as e:
            print(f"Error loading policies in form: {e}")
            self.fields['policy_name'].choices = [('', '-- No policies available --')]


class NetworkProviderForm(forms.ModelForm):
    class Meta:
        model = NetworkProvider
        fields = [
            'provider_id', 'hospital_name', 'location', 'contact',
            'email', 'type', 'network_type', 'coverage_limit', 'status'
        ]
        widgets = {
            'provider_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., PROV001'
            }),
            'hospital_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Hospital Name'
            }),
            'location': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Full address'
            }),
            'contact': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@hospital.com'
            }),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'network_type': forms.Select(attrs={'class': 'form-select'}),
            'coverage_limit': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., $10,000 per year'
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_provider_id(self):
        provider_id = self.cleaned_data.get('provider_id')

        # Check if provider_id already exists (for create view)
        if not self.instance.pk:  # New instance
            if NetworkProvider.objects.filter(provider_id=provider_id).exists():
                raise forms.ValidationError('Provider ID already exists. Please choose a different one.')

        return provider_id

    def clean_contact(self):
        contact = self.cleaned_data.get('contact')
        # Add any contact validation here
        if len(contact) < 10:
            raise forms.ValidationError('Contact number should be at least 10 digits.')
        return contact

