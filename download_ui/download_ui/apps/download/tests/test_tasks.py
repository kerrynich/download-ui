import os
from unittest.mock import MagicMock, patch

from celery.exceptions import SoftTimeLimitExceeded
from django.test import TestCase

from download_ui.apps.download.models import Download, Command, Extension, Format, Quality, Source
from download_ui.apps.download.tasks import worker_download, check_for_missing_files
from download_ui.apps.download.exceptions import DownloadError


class MockedRequest:
    def __init__(self, req_id=None):
        self.id = req_id or '1'


class MockedTask:
    def __init__(self, req_id=None):
        self.request = MockedRequest(req_id=req_id)

    def AsyncResult(self, _id):
        return MagicMock(info={'filename': 'test_file.txt'})


class WorkerDownloadTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        filename = 'test_file.txt'
        with open(filename, 'w', encoding='utf8') as fp:
            fp.write("New test file created")

        command1 = Command.objects.create(name='YTDL')

        quality1 = Quality.objects.create(name='720p')
        extension1 = Extension.objects.create(name='mkv')
        format1 = Format.objects.create(format_code='64',
                                        quality=quality1,
                                        command=command1,
                                        extension=extension1)

        source1 = Source.objects.create(name='Youtube')
        Download.objects.create(
            command=command1,
            source=source1,
            url='https://youtube.com',
            title='Title Youtube',
            slug_id='youtubeslug',
            file_format=format1,
            status=Download.Status.STARTED
        )
        command2 = Command.objects.create(name='TWDL')

        quality2 = Quality.objects.create(name='360p')
        extension2 = Extension.objects.create(name='mp3')
        format2 = Format.objects.create(format_code='54',
                                        quality=quality2,
                                        command=command2,
                                        extension=extension2)

        source2 = Source.objects.create(name='Twitch')
        Download.objects.create(
            command=command2,
            source=source2,
            url='https://twitch.com',
            title='Title Twitch',
            slug_id='twitchslug',
            file_format=format2,
            status=Download.Status.STARTED
        )

        Download.objects.create(
            command=command2,
            source=source2,
            url='https://twitch.com',
            title='Title File Present',
            slug_id='twitchfile',
            file_format=format2,
            file_path=filename,
            status=Download.Status.COMPLETED
        )

    @classmethod
    def tearDownClass(cls):
        super(WorkerDownloadTest, cls).tearDownClass()
        os.remove('test_file.txt')

    @patch("download_ui.apps.download.tasks.Downloader.get_downloader")
    def test_task_successful_youtubedl(self, mocked_downloader):
        mocked_downloader.return_value = MagicMock(
            download=MagicMock(), format_size=MagicMock(return_value='84MB'))
        mocked_task = MockedTask(req_id='test-id-celery-1')

        worker_download(self=mocked_task, download_id=1)

        download = Download.objects.get(id=1)
        self.assertEqual(download.active_task_id, 'test-id-celery-1')
        self.assertEqual(download.file_path, 'test_file.txt')
        self.assertEqual(download.size, '84MB')
        self.assertEqual(download.status, Download.Status.COMPLETED)

    @patch("download_ui.apps.download.tasks.Downloader.get_downloader")
    def test_task_twitchdl_file_failure(self, mocked_downloader):
        mocked_downloader.return_value = MagicMock(
            download=MagicMock(), format_size=MagicMock(side_effect=OSError('File not Found')))
        mocked_task = MockedTask(req_id='test-id-celery-2')

        worker_download(self=mocked_task, download_id=2)

        download = Download.objects.get(id=2)
        self.assertEqual(download.active_task_id, 'test-id-celery-2')
        self.assertEqual(download.file_path, 'test_file.txt')
        self.assertEqual(download.size, 'N/A')
        self.assertEqual(download.status, Download.Status.FAILED)

    @patch("download_ui.apps.download.tasks.Downloader.get_downloader")
    def test_task_twitchdl_download_failure(self, mocked_downloader):
        mocked_downloader.return_value = MagicMock(
            download=MagicMock(side_effect=DownloadError('twitch-dl', 'Download failed to work')))
        mocked_task = MockedTask(req_id='test-id-celery-2')

        worker_download(self=mocked_task, download_id=2)

        download = Download.objects.get(id=2)
        self.assertEqual(download.active_task_id, 'test-id-celery-2')
        self.assertEqual(download.file_path, 'N/A')
        self.assertEqual(download.size, 'N/A')
        self.assertEqual(download.status, Download.Status.FAILED)

    @patch("download_ui.apps.download.tasks.Downloader.get_downloader")
    def test_task_twitchdl_soft_time_limit(self, mocked_downloader):
        mocked_downloader.return_value = MagicMock(
            download=MagicMock(side_effect=SoftTimeLimitExceeded))
        mocked_task = MockedTask(req_id='test-id-celery-2')

        worker_download(self=mocked_task, download_id=2)

        download = Download.objects.get(id=2)
        self.assertEqual(download.active_task_id, 'test-id-celery-2')
        self.assertEqual(download.file_path, 'N/A')
        self.assertEqual(download.size, 'N/A')
        self.assertEqual(download.status, Download.Status.TERMINATED)

    def test_task_periodic_missing_files_check(self):
        download = Download.objects.get(id=3)
        self.assertEqual(download.status, Download.Status.COMPLETED)
        os.remove('test_file.txt')

        check_for_missing_files()

        download = Download.objects.get(id=3)
        self.assertEqual(download.file_path, 'test_file.txt')
        self.assertEqual(download.status, Download.Status.MISSING)
        with open('test_file.txt', 'w', encoding='utf8') as fp:
            fp.write("New test file created")
