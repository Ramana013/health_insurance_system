from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import CustomUser


class UserRegisterForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'phone', 'dob', 'address', 'role', 'password1', 'password2']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data['phone']
        user.dob = self.cleaned_data['dob']
        user.address = self.cleaned_data['address']
        user.role = self.cleaned_data['role']
        
        if commit:
            user.save()
        return user
        
class LoginForm(AuthenticationForm):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)