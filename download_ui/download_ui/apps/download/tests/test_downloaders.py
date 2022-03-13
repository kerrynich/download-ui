import os
from unittest.mock import MagicMock, patch
from django.conf import settings

from celery.exceptions import SoftTimeLimitExceeded
from django.test import TestCase
from youtube_dl.utils import UnsupportedError, ExtractorError

from download_ui.apps.download.exceptions import DownloadError, ExtractionError
from download_ui.apps.download.downloaders.downloader import YoutubeDownloader, Downloader, TwitchDownloader


class DownloaderTest(TestCase):
    def test_get_downloader_no_args(self):
        downloader = Downloader.get_downloader('YTDL')
        self.assertIsInstance(downloader, YoutubeDownloader)

    def test_get_downloader_just_task(self):
        task_mock = MagicMock()
        downloader = Downloader.get_downloader('YTDL', task=task_mock)
        self.assertIsInstance(downloader, YoutubeDownloader)
        self.assertEqual(downloader.task, task_mock)

    def test_get_downloader_task_and_code(self):
        task_mock = MagicMock()
        downloader = Downloader.get_downloader(
            'YTDL', task=task_mock, code='testcode')
        self.assertIsInstance(downloader, YoutubeDownloader)
        self.assertEqual(downloader.task, task_mock)
        self.assertFalse(downloader.two_stages)

    def test_get_twitch_downloader_task_and_code(self):
        task_mock = MagicMock()
        downloader = Downloader.get_downloader(
            'TWDL', task=task_mock, code='testcode')
        self.assertIsInstance(downloader, TwitchDownloader)
        self.assertEqual(downloader.task, task_mock)


class YoutubeDownloaderTest(TestCase):
    @patch("youtube_dl.YoutubeDL")
    def test_downloader_extract_combined_files(self, mocked_youtube_dl):
        result_data = {
            'channel': 'youtube lady',
            'title': 'Test Video',
            'id': 'gibberish',
            'extractor_key': 'Youtube',
            'formats': [
                {
                    'vcodec': 'something',
                    'acodec': 'something',
                    'format_id': '64',
                    'ext': 'mkv',
                    'resolution': '720p'

                },
                {
                    'vcodec': 'something',
                    'acodec': 'something',
                    'format_id': '84',
                    'ext': 'mp3',
                    'height': '240',
                    'width': '360',
                },
                {
                    'vcodec': 'something',
                    'acodec': 'none',
                    'format_id': '74',
                    'ext': 'mkv',
                    'height': '240',
                },
                {
                    'vcodec': 'something',
                    'acodec': 'none',
                    'format_id': '14',
                    'ext': 'mp3',
                },
                {
                    'vcodec': 'none',
                    'acodec': 'none',
                    'format_id': '24',
                    'ext': 'mkv',
                    'height': '240',
                }
            ]
        }
        mocked_youtube_dl.return_value = MagicMock(
            extract_info=MagicMock(return_value=result_data))

        downloader = YoutubeDownloader()
        result = downloader.extract('www.youtube.com/watch?v=gibberish')

        self.assertEqual(result['channel_name'], 'youtube lady')
        self.assertEqual(result['title'], 'Test Video')
        self.assertEqual(result['slug_id'], 'gibberish')
        self.assertEqual(result['source'], 'Youtube')
        self.assertSequenceEqual(result['format_info'], [(
            'mkv', '720p', '64'), ('mp3', '360x240', '84')])

    @patch("youtube_dl.YoutubeDL")
    def test_downloader_extract_audio_and_video_files(self, mocked_youtube_dl):
        result_data = {
            'channel': 'youtube lady',
            'title': 'Test Video',
            'id': 'gibberish',
            'extractor_key': 'Youtube',
            'formats': [
                {
                    'vcodec': 'none',
                    'acodec': 'something',
                    'format_id': '64',
                    'ext': 'mkv',
                    'resolution': '720p'

                },
                {
                    'vcodec': 'something',
                    'acodec': 'none',
                    'format_id': '74',
                    'ext': 'mp3',
                    'width': '360',
                },
                {
                    'vcodec': 'something',
                    'acodec': 'none',
                    'format_id': '84',
                    'ext': 'mkv',
                    'height': '240',
                },
                {
                    'vcodec': 'something',
                    'acodec': 'something',
                    'format_id': '94',
                    'ext': 'mp3',
                    'height': '240',
                    'width': '360',
                }
            ]
        }
        mocked_youtube_dl.return_value = MagicMock(
            extract_info=MagicMock(return_value=result_data))

        downloader = YoutubeDownloader()
        result = downloader.extract('www.youtube.com/watch?v=gibberish')

        self.assertSequenceEqual(result['format_info'], [(
            'mp3', '360x?', '74+bestaudio'), ('mkv', '240p', '84+bestaudio')])

    @patch("youtube_dl.YoutubeDL")
    def test_downloader_extract_result_none(self, mocked_youtube_dl):
        mocked_youtube_dl.return_value = MagicMock(
            extract_info=MagicMock(return_value=None))

        downloader = YoutubeDownloader()

        with self.assertRaisesMessage(ExtractionError, 'Download Information not found'):
            downloader.extract('www.youtube.com/watch?v=gibberish')

    @patch("youtube_dl.YoutubeDL")
    def test_downloader_extract_exception_extract_info(self, mocked_youtube_dl):
        weird_exception = ExtractorError('Generic Message')
        weird_exception.exc_info = (
            None, UnsupportedError('www.google.com'), None)
        mocked_youtube_dl.return_value = MagicMock(
            extract_info=MagicMock(side_effect=weird_exception))

        downloader = YoutubeDownloader()

        with self.assertRaisesMessage(ExtractionError, 'Unsupported URL: www.google.com'):
            downloader.extract('www.google.com')

    @patch("youtube_dl.YoutubeDL")
    def test_downloader_download_success(self, mocked_youtube_dl):
        mocked_youtube_dl.return_value = MagicMock(
            download=MagicMock(return_value="something"))

        downloader = YoutubeDownloader()
        result = downloader.download(
            'www.youtube.com/watch?v=gibberish', '74', 1)

        self.assertEqual(result, 'something')

    @patch("youtube_dl.YoutubeDL")
    def test_downloader_download_exception(self, mocked_youtube_dl):
        weird_exception = ExtractorError('Generic Message')
        weird_exception.exc_info = (
            None, UnsupportedError('www.google.com'), None)
        mocked_youtube_dl.return_value = MagicMock(
            download=MagicMock(side_effect=weird_exception))

        downloader = YoutubeDownloader()
        with self.assertRaisesMessage(DownloadError, 'Unsupported URL: www.google.com'):
            downloader.download('www.google.com', '74', 1)

    @patch("youtube_dl.YoutubeDL")
    def test_downloader_download_timeout_exception(self, mocked_youtube_dl):
        mocked_youtube_dl.return_value = MagicMock(
            download=MagicMock(side_effect=SoftTimeLimitExceeded))

        downloader = YoutubeDownloader()
        with self.assertRaisesMessage(SoftTimeLimitExceeded, 'SoftTimeLimitExceeded()'):
            downloader.download('www.google.com', '74', 1)

    def test_downloader_download_opts(self):
        downloader = YoutubeDownloader()
        mock_hook = MagicMock()
        options = downloader.get_download_opts(mock_hook, 'testcode', 3)
        self.assertEqual(options['format'], 'testcode')
        self.assertEqual(options['outtmpl'], os.path.join(
            settings.FILE_PATH_FIELD_DIRECTORY,
            '%(extractor_key)s/%(title)s-3-%(resolution)s.%(ext)s'))
        self.assertSequenceEqual(options['progress_hooks'], [mock_hook])
        self.assertTrue(options['restrictfilenames'])
        self.assertTrue(options['noplaylist'])
        self.assertTrue(options['nooverwrites'])

    @patch("youtube_dl.utils.format_bytes")
    def test_downloader_format_size(self, mocked_format_bytes):
        mocked_format_bytes.return_value = '23567'

        downloader = YoutubeDownloader()
        result = downloader.format_size(23456)

        self.assertEqual(result, '23567')

    def test_my_hook_finished_one_stage(self):
        mocked_update_state = MagicMock()
        mocked_task = MagicMock(update_state=mocked_update_state)
        downloader = YoutubeDownloader(task=mocked_task, code='64')

        info = {
            'status': 'finished',
            'filename': 'my_file.txt'
        }
        downloader.my_hook(info)
        args, kwargs = mocked_update_state.call_args
        self.assertEqual(kwargs['state'], 'FILENAME')
        self.assertEqual(kwargs['meta']['filename'], 'my_file.txt')

    def test_my_hook_finished_two_stages_first_stage(self):
        mocked_update_state = MagicMock()
        mocked_task = MagicMock(update_state=mocked_update_state)
        downloader = YoutubeDownloader(task=mocked_task, code='64+bestaudio')

        info = {
            'status': 'finished',
            'filename': 'my_file.tmp.txt'
        }
        downloader.my_hook(info)
        self.assertFalse(downloader.first_stage)
        self.assertEqual(downloader.final_filename, 'my_file.txt')

    def test_my_hook_finished_two_stages_second_stage(self):
        mocked_update_state = MagicMock()
        mocked_task = MagicMock(update_state=mocked_update_state)
        downloader = YoutubeDownloader(task=mocked_task, code='64+bestaudio')
        downloader.first_stage = False
        downloader.final_filename = 'my_file.txt'

        info = {
            'status': 'finished',
            'filename': 'new_file.txt'
        }
        downloader.my_hook(info)
        args, kwargs = mocked_update_state.call_args
        self.assertEqual(kwargs['state'], 'FILENAME')
        self.assertEqual(kwargs['meta']['filename'], 'my_file.txt')

    def test_my_hook_downloading_one_stage(self):
        mocked_update_state = MagicMock()
        mocked_task = MagicMock(update_state=mocked_update_state)
        downloader = YoutubeDownloader(task=mocked_task, code='64')

        info = {
            'status': 'downloading',
            '_percent_str': '  19.6%  ',
            '_eta_str': '2:00 s'
        }
        downloader.my_hook(info)
        args, kwargs = mocked_update_state.call_args
        self.assertEqual(kwargs['state'], 'PROGRESS')
        self.assertEqual(kwargs['meta']['percent_str'], '19.6%')
        self.assertEqual(kwargs['meta']['percent'], '20')

    def test_my_hook_downloading_two_stages_first_stage(self):
        mocked_update_state = MagicMock()
        mocked_task = MagicMock(update_state=mocked_update_state)
        downloader = YoutubeDownloader(task=mocked_task, code='64+bestaudio')

        info = {
            'status': 'downloading',
            '_percent_str': '  19.6%  ',
            '_eta_str': '2:00 s'
        }
        downloader.my_hook(info)
        args, kwargs = mocked_update_state.call_args
        self.assertEqual(kwargs['state'], 'PROGRESS')
        self.assertEqual(kwargs['meta']['percent_str'], '9.8%')
        self.assertEqual(kwargs['meta']['percent'], '10')

    def test_my_hook_downloading_two_stages_second_stage(self):
        mocked_update_state = MagicMock()
        mocked_task = MagicMock(update_state=mocked_update_state)
        downloader = YoutubeDownloader(task=mocked_task, code='64+bestaudio')
        downloader.first_stage = False

        info = {
            'status': 'downloading',
            '_percent_str': '  19.6%  ',
            '_eta_str': '2:00 s'
        }
        downloader.my_hook(info)
        args, kwargs = mocked_update_state.call_args
        self.assertEqual(kwargs['state'], 'PROGRESS')
        self.assertEqual(kwargs['meta']['percent_str'], '59.8%')
        self.assertEqual(kwargs['meta']['percent'], '60')


class TwitchDownloaderTest(TestCase):
    @patch("download_ui.apps.download.downloaders.downloader.utils.format_size")
    def test_downloader_format_size(self, mocked_format_size):
        mocked_format_size.return_value = '23567'

        downloader = TwitchDownloader()
        result = downloader.format_size(23456)

        self.assertEqual(result, '23567')

    def test_downloader_download_opts(self):
        downloader = TwitchDownloader()
        options = downloader.get_download_opts(
            'www.testurl.com', 'testcode', 3)
        self.assertEqual(options.video, 'www.testurl.com')
        self.assertEqual(options.output, os.path.join(
            settings.FILE_PATH_FIELD_DIRECTORY,
            'twitch/{title_slug}-3-testcode.{format}'))
        self.assertEqual(options.quality, 'testcode')
        self.assertFalse(options.overwrite)

    def test_downloader_extract_opts(self):
        downloader = TwitchDownloader()
        options = downloader.get_extract_opts('www.testurl.com')
        self.assertEqual(options.identifier, 'www.testurl.com')
        self.assertTrue(options.json)
