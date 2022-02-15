from django import forms

from .models import Download, Format

class DownloadForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    class Meta:
        model = Download
        fields = ('command', 'url')

class DownloadFormatForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_format'].queryset = Format.objects.filter(choices__id=self.initial['id'])

    class Meta:
        model = Download
        fields = ('id', 'command', 'url', 'file_format')
