from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.mail import mail_admins
from django.utils.translation import gettext_lazy as _get

from .models import Download, Format, UserProfile


class DownloadForm(forms.ModelForm):
    class Meta:
        model = Download
        fields = ('command', 'url')


class DownloadFormatForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_format'].queryset = Format.objects.filter(
            choices__id=self.initial['id'])

    class Meta:
        model = Download
        fields = ('id', 'command', 'url', 'file_format')


class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = UserProfile
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super(UserRegisterForm, self).save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()

    def send_email(self):
        # send email using the self.cleaned_data dictionary
        mail_admins('New User Registration Request',
                    f'Go approve the new user ({self.instance.username}) in the admin console.')


class RestrictedAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        print('hello made it in')
        if not user.is_approved:
            raise forms.ValidationError(
                _get("This account has not yet been approved by an Admin."),
                code='unapproved',
            )
