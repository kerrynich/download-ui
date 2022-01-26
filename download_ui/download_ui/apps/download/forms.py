from django import forms
from django.conf import settings
from .models import Download

class DownloadForm(forms.ModelForm):
    def save(self, commit=True):
        self.instance.title = "Test Title: " + self.instance.url
        base = settings.FILE_PATH_FIELD_DIRECTORY
        source_label = self.instance.source.get_source_display()
        self.instance.file_path = base + '/' + source_label + '/' + 'new_file_baby.mp3'
        return super(DownloadForm, self).save(commit)

    class Meta:
        model = Download
        fields = ('source', 'url')