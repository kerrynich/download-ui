from django.forms import URLField
from django.test import TestCase

from download_ui.apps.download.forms import DownloadForm, DownloadFormatForm
from download_ui.apps.download.models import Command, Source, Quality, Extension, Format, Download


class DownloadFormTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        quality = Quality.objects.create(name='720p')
        extension = Extension.objects.create(name='mkv')
        format_test = Format.objects.create(format_code='64',
                                            quality=quality,
                                            command=command,
                                            extension=extension)
        source = Source.objects.create(name='Youtube')
        download = Download.objects.create(command=command,
                                           source=source,
                                           url='https://www.youtube.com',
                                           title='Testing Title 123')
        download.choices_for.add(format_test)

    def test_download_form_field_labels(self):
        form = DownloadForm()
        self.assertEqual(len(form.fields), 2)
        self.assertTrue(
            form.fields['url'].label is None or form.fields['url'].label == 'Url')
        self.assertFieldOutput(URLField, {
                               'https://www.youtube.com': 'https://www.youtube.com'}, {'aaa': ['Enter a valid URL.']})
        self.assertTrue(
            form.fields['command'].label is None or form.fields['command'].label == 'Command'
        )

    def test_download_format_form_field_labels(self):
        form = DownloadFormatForm(initial={'id': 1})
        self.assertEqual(len(form.fields), 3)
        self.assertTrue(
            form.fields['url'].label is None or form.fields['url'].label == 'Url')
        self.assertTrue(
            form.fields['command'].label is None or form.fields['command'].label == 'Command'
        )
        self.assertTrue(
            form.fields['file_format'].label is None or form.fields['file_format'].label == 'File format'
        )
        self.assertEqual(form.fields['file_format'].queryset.count(), 1)
        self.assertEqual(form.fields['file_format'].queryset.all()[0].id, 1)
