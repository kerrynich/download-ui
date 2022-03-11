import os
from unittest.mock import MagicMock, patch
from django.forms import ValidationError

from django.test import TestCase

from download_ui.apps.download.models import Command, Source, Quality, Extension, Format, Download
from download_ui.apps.download.exceptions import ExtractionError


class DownloadModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Twitch')
        Download.objects.create(command=command,
                                source=source,
                                url='https://www.twitch.com',
                                title='Testing Title 123')
        quality = Quality.objects.create(name='720p')
        extension = Extension.objects.create(name='mkv')
        Format.objects.create(format_code='64',
                              quality=quality,
                              command=command,
                              extension=extension)

    def test_object_name_is_display_name(self):
        download = Download.objects.get(id=1)
        expected_object_name = download.title
        self.assertEqual(str(download), expected_object_name)

    def test_get_absolute_url(self):
        download = Download.objects.get(id=1)
        self.assertEqual(download.get_absolute_url(), '/download/1/')

    def test_set_missing_if_file_not_found_is_missing(self):
        download = Download.objects.get(id=1)
        download.status = Download.Status.COMPLETED
        download.file_path = "test_file_does_not_exist"
        download.set_missing_if_file_not_found()
        self.assertEqual(download.status, Download.Status.MISSING)

    def test_set_missing_if_file_not_found_is_not_missing(self):
        download = Download.objects.get(id=1)
        download.status = Download.Status.COMPLETED
        download.file_path = os.getcwd()
        download.set_missing_if_file_not_found()
        self.assertEqual(download.status, Download.Status.COMPLETED)

    def test_archive_download_no_file(self):
        download = Download.objects.get(id=1)
        download.file_path = "test_file_does_not_exist"
        download.archive_download()
        self.assertEqual(download.status, Download.Status.ARCHIVED)

    def test_archive_download_file_exists(self):
        download = Download.objects.get(id=1)
        filename = 'test_file.txt'
        with open(filename, 'w', encoding='utf8') as fp:
            fp.write("New test file created")
        download.file_path = filename
        self.assertTrue(os.path.exists(filename))
        download.archive_download()
        self.assertTrue(not os.path.exists(filename))
        self.assertEqual(download.status, Download.Status.ARCHIVED)

    @patch("download_ui.apps.download.models.Downloader.get_downloader")
    def test_clean_fields(self, mocked_downloader):
        mocked_extract = MagicMock()
        mocked_extract.side_effect = ExtractionError(
            'youtube-dl', 'Extraction failed to work')
        mocked_downloader.return_value = MagicMock(extract=mocked_extract)
        download = Download()
        download.url = 'https://www.youtube.com/watch?v=currentslug'
        download.command = Command.objects.get(id=1)

        with self.assertRaisesMessage(ValidationError, 'Download failure: Extraction failed to work'):
            download.clean_fields(exclude=[
                                  'source', 'file_path', 'title', 'slug_id', 'channel_name', 'size', 'active_task_id'])

    def test_save_first_save_with_format_ids(self):
        download = Download()
        format_test = Format.objects.get(id=1)
        download.command = Command.objects.get(id=1)
        download.source = Source.objects.get(id=1)
        download.format_ids = [format_test.id]
        self.assertTrue(not download.id)
        download.save()
        self.assertTrue(download.id)
        self.assertEqual(download.choices_for.count(), 1)
        self.assertEqual(download.choices_for.all()[0].id, format_test.id)

    def test_save_second_save_with_format_ids(self):
        download = Download.objects.get(id=1)
        format_test = Format.objects.get(id=1)
        download.format_ids = [format_test.id]
        self.assertTrue(download.id)
        self.assertEqual(download.choices_for.count(), 0)
        download.save()
        self.assertTrue(download.id)
        self.assertEqual(download.choices_for.count(), 0)


class CommandModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Command.objects.create(name='YTDL')

    def test_object_name_is_display_name(self):
        command = Command.objects.get(id=1)
        expected_object_name = Command.CommandName.YOUTUBEDL.label
        self.assertEqual(str(command), expected_object_name)


class SourceModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Source.objects.create(name='twitch')

    def test_object_name_is_display_name(self):
        source = Source.objects.get(id=1)
        expected_object_name = source.name
        self.assertEqual(str(source), expected_object_name)


class QualityModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Quality.objects.create(name='720p')

    def test_object_name_is_display_name(self):
        quality = Quality.objects.get(id=1)
        expected_object_name = quality.name
        self.assertEqual(str(quality), expected_object_name)


class ExtensionModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        Extension.objects.create(name='mkv')

    def test_object_name_is_display_name(self):
        extension = Extension.objects.get(id=1)
        expected_object_name = extension.name
        self.assertEqual(str(extension), expected_object_name)


class FormatModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        quality = Quality.objects.create(name='720p')
        extension = Extension.objects.create(name='mkv')
        Format.objects.create(format_code='64',
                              quality=quality,
                              command=command,
                              extension=extension)

    def test_object_name_is_ext_and_qual(self):
        format_test = Format.objects.get(id=1)
        expected_object_name = f'{format_test.extension.name} : {format_test.quality.name}'
        self.assertEqual(str(format_test), expected_object_name)
