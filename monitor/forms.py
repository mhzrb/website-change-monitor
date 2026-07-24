from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import WatchedSite


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=True, help_text="Required — this is where change alerts get sent.")

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class WatchedSiteForm(forms.ModelForm):
    class Meta:
        model = WatchedSite
        fields = ["name", "url", "css_selector", "check_frequency_minutes"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "e.g. IND visa page"}),
            "url": forms.URLInput(attrs={"class": "form-control", "placeholder": "https://..."}),
            "css_selector": forms.TextInput(attrs={"class": "form-control", "placeholder": "#content (optional)"}),
            "check_frequency_minutes": forms.Select(attrs={"class": "form-select"}),
        }
