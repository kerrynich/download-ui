from datetime import timedelta
import os
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from download_ui.apps.download.models import Command, Extension, Quality, Source, Download, Format


class DownloadHomeViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        number_of_fresh_downloads = 2

        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Youtube')

        Download.objects.create(
            command=command,
            source=source,
            url='URL',
            title='Title Draft',
            status=Download.Status.DRAFT
        )

        download_old = Download.objects.create(
            command=command,
            source=source,
            url='URL',
            title='Title Old',
            status=Download.Status.STARTED
        )
        download_old.created_at = timezone.now() - timedelta(hours=26)
        download_old.save()

        for down_id in range(number_of_fresh_downloads):
            Download.objects.create(
                command=command,
                source=source,
                url=f'URL {down_id}',
                title=f'Title {down_id}',
                status=Download.Status.STARTED
            )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('download:home'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('download:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'download_home.html')

    def test_downloads_only_today(self):
        # Test downloads only includes ones from today and not drafts
        response = self.client.get(reverse('download:home'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('downloads' in response.context)
        self.assertEqual(len(response.context['downloads']), 2)
        for download in response.context['downloads']:
            self.assertTrue(download.id in [3, 4])
            self.assertGreater(download.created_at,
                               timezone.now() - timedelta(hours=24))


class DownloadCreateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command1 = Command.objects.create(name='YTDL')
        Command.objects.create(name='TWDL')

        source = Source.objects.create(name='Youtube')

        Download.objects.create(
            command=command1,
            source=source,
            url='URL',
            title='Title Original',
            status=Download.Status.STARTED
        )

        Download.objects.create(
            command=command1,
            source=source,
            url='https://youtube.com',
            title='Title Current',
            slug_id='currentslug',
            status=Download.Status.DRAFT
        )

        filename = 'test_file.txt'
        with open(filename, 'w', encoding='utf8') as fp:
            fp.write("New test file created")
        Download.objects.create(
            command=command1,
            source=source,
            url='https://youtube.com',
            title='Title Current',
            slug_id='currentslug',
            file_path=filename,
            status=Download.Status.COMPLETED
        )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/create/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('download:create'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('download:create'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/download_form.html')

    def test_view_refresh_after_update_get(self):
        default_task_info = {'percent_str': '0.0%', 'percent': 0.0}
        response = self.client.get(reverse('download:create')+'?old_pk=1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['download'].id, 1)
        self.assertEqual(response.context['trigger'], 'load delay:600ms')
        self.assertEqual(response.context['task_info'], default_task_info)

    @patch("download_ui.apps.download.models.Downloader.get_downloader")
    def test_view_successful_post(self, mocked_downloader):
        mocked_extract = MagicMock()
        mocked_extract.return_value = {
            'source': 'Youtube',
            'title': 'Test Title',
            'slug_id': 'sluggy',
            'channel_name': 'youtuber man',
            'format_info': [('mkv', '720p', '54'), ('mp4', '360p', '36')]
        }
        mocked_downloader.return_value = MagicMock(extract=mocked_extract)
        test_url = 'https://google.com'
        test_command = 1
        response = self.client.post(reverse('download:create'), {
                                    'command': test_command, 'url': test_url})
        self.assertRedirects(response, reverse(
            'download:update', kwargs={'pk': 4}))
        download = Download.objects.get(id=4)
        self.assertEqual(download.url, test_url)
        self.assertEqual(download.command.id, test_command)
        self.assertEqual(download.status, Download.Status.DRAFT)
        self.assertEqual(download.source.name, 'Youtube')
        self.assertEqual(download.title, 'Test Title')
        self.assertEqual(download.slug_id, 'sluggy')
        self.assertEqual(download.channel_name, 'youtuber man')

    @patch("download_ui.apps.download.models.Downloader.get_downloader")
    def test_view_invalid_post(self, mocked_downloader):
        mocked_extract = MagicMock()
        mocked_extract.return_value = {
            'source': 'Youtube',
            'title': 'Test Title',
            'slug_id': 'sluggy',
            'channel_name': 'youtuber man',
            'format_info': [('mkv', '720p', '54'), ('mp4', '360p', '36')]
        }
        mocked_downloader.return_value = MagicMock(extract=mocked_extract)
        test_url = 'gibberish'
        test_command = 1
        response = self.client.post(reverse('download:create'), {
                                    'command': test_command, 'url': test_url})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'url', ['Enter a valid URL.'])

    @patch("download_ui.apps.download.models.Downloader.get_downloader")
    def test_view_successful_post_draft_exists_and_other_file(self, mocked_downloader):
        mocked_extract = MagicMock()
        mocked_extract.return_value = {
            'source': 'Youtube',
            'title': 'Title Current',
            'slug_id': 'currentslug',
            'channel_name': 'youtuber man',
            'format_info': [('mkv', '720p', '54'), ('mp4', '360p', '36')]
        }
        mocked_downloader.return_value = MagicMock(extract=mocked_extract)
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse('download:create'), {
                                    'command': test_command, 'url': test_url})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/download_form.html')
        self.assertEqual(response.context['download'].slug_id, 'currentslug')
        self.assertEqual(len(response.context['existing']), 1)
        self.assertEqual(response.context['existing'][0].id, 3)
        self.assertEqual(response.context['modal_title'], 'Video Exists')
        self.assertEqual(response.context['modal_body'], [
            'This video has already been downloaded in the following quality(s).',
            'Please select to skip a fresh download and use an existing file.'
        ])

    @patch("download_ui.apps.download.models.Downloader.get_downloader")
    def test_view_successful_post_override(self, mocked_downloader):
        mocked_extract = MagicMock()
        mocked_extract.return_value = {
            'source': 'Youtube',
            'title': 'Title Current',
            'slug_id': 'currentslug',
            'channel_name': 'youtuber man',
            'format_info': [('mkv', '720p', '54'), ('mp4', '360p', '36')]
        }
        mocked_downloader.return_value = MagicMock(extract=mocked_extract)
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse(
            'download:create')+'?override', {'command': test_command, 'url': test_url})
        self.assertRedirects(response, reverse(
            'download:update', kwargs={'pk': 4}))
        download = Download.objects.get(id=4)
        self.assertEqual(download.url, test_url)
        self.assertEqual(download.command.id, test_command)

    @patch("download_ui.apps.download.models.Downloader.get_downloader")
    def test_view_successful_post_download_exists_but_file_missing(self, mocked_downloader):
        mocked_extract = MagicMock()
        mocked_extract.return_value = {
            'source': 'Youtube',
            'title': 'Title Current',
            'slug_id': 'currentslug',
            'channel_name': 'youtuber man',
            'format_info': [('mkv', '720p', '54'), ('mp4', '360p', '36')]
        }
        mocked_downloader.return_value = MagicMock(extract=mocked_extract)
        os.remove('test_file.txt')
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse('download:create'), {
                                    'command': test_command, 'url': test_url})
        self.assertRedirects(response, reverse(
            'download:update', kwargs={'pk': 4}))
        download = Download.objects.get(id=4)
        self.assertEqual(download.url, test_url)
        self.assertEqual(download.command.id, test_command)
        with open('test_file.txt', 'w', encoding='utf8') as fp:
            fp.write("New test file created")


class DownloadUpdateViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command1 = Command.objects.create(name='YTDL')
        Command.objects.create(name='TWDL')

        source = Source.objects.create(name='Youtube')
        quality = Quality.objects.create(name='720p')
        extension = Extension.objects.create(name='mkv')
        format_test = Format.objects.create(format_code='64',
                                            quality=quality,
                                            command=command1,
                                            extension=extension)

        filename = 'test_file.txt'
        with open(filename, 'w', encoding='utf8') as fp:
            fp.write("New test file created")
        Download.objects.create(
            command=command1,
            source=source,
            url='https://youtube.com',
            title='Title Current',
            slug_id='currentslug',
            file_path=filename,
            file_format=format_test,
            status=Download.Status.COMPLETED
        )

        new_download = Download.objects.create(
            command=command1,
            source=source,
            url='https://youtube.com',
            title='Title Current',
            slug_id='newslug',
            status=Download.Status.DRAFT
        )
        new_download.choices_for.add(format_test)

        started_download = Download.objects.create(
            command=command1,
            source=source,
            url='https://youtube.com',
            title='Title Current',
            slug_id='currentslug',
            status=Download.Status.DRAFT
        )
        started_download.choices_for.add(format_test)

    @classmethod
    def tearDownClass(cls):
        super(DownloadUpdateViewTest, cls).tearDownClass()
        os.remove('test_file.txt')

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/2/update/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(
            reverse('download:update', kwargs={'pk': 2}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(
            reverse('download:update', kwargs={'pk': 2}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/download_format_form.html')

    def test_view_intial_id_present(self):
        response = self.client.get(
            reverse('download:update', kwargs={'pk': 2}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['form'].initial['id'], 2)

    @patch("download_ui.apps.download.views.worker_download")
    def test_view_successful_post(self, _mocked_worker):
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse('download:update', kwargs={'pk': 2}), {
                                    'command': test_command, 'url': test_url, 'id': 2, 'file_format': 1})
        self.assertRedirects(response, reverse('download:create')+'?old_pk=2')
        download = Download.objects.get(id=2)
        self.assertEqual(download.url, test_url)
        self.assertEqual(download.command.id, test_command)
        self.assertEqual(download.status, Download.Status.STARTED)
        self.assertEqual(download.file_format.id, 1)

    def test_view_invalid_post(self):
        test_url = 'gibberish'
        test_command = 1
        response = self.client.post(reverse('download:update', kwargs={'pk': 2}), {
                                    'command': test_command, 'url': test_url, 'id': 2, 'file_format': 1})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, 'form', 'url', ['Enter a valid URL.'])

    def test_view_successful_post_other_file(self):
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse('download:update', kwargs={'pk': 3}), {
                                    'command': test_command, 'url': test_url, 'id': 3, 'file_format': 1})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/download_format_form.html')
        self.assertEqual(response.context['download'].slug_id, 'currentslug')
        self.assertEqual(len(response.context['existing']), 1)
        self.assertEqual(response.context['existing'][0].id, 1)
        self.assertEqual(
            response.context['modal_title'], 'Video with this Format Exists')
        self.assertEqual(response.context['modal_body'], [
            'This video has already been downloaded in this quality & format.',
            'Please select to skip a fresh download and use the existing file.'
        ])
        self.assertTrue(response.context['update'])

    @patch("download_ui.apps.download.views.worker_download")
    def test_view_successful_post_override(self, _mocked_worker):
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse(
            'download:update', kwargs={'pk': 3})+'?override', {'command': test_command, 'url': test_url, 'id': 3, 'file_format': 1})
        self.assertRedirects(response, reverse('download:create')+'?old_pk=3')
        download = Download.objects.get(id=3)
        self.assertEqual(download.url, test_url)
        self.assertEqual(download.command.id, test_command)

    @patch("download_ui.apps.download.views.worker_download")
    def test_view_successful_post_download_exists_but_file_missing(self, _mocked_worker):
        os.remove('test_file.txt')
        test_url = 'https://youtube.com'
        test_command = 1
        response = self.client.post(reverse('download:update', kwargs={'pk': 3}), {
                                    'command': test_command, 'url': test_url, 'id': 3, 'file_format': 1})
        self.assertRedirects(response, reverse('download:create')+'?old_pk=3')
        download = Download.objects.get(id=3)
        self.assertEqual(download.url, test_url)
        self.assertEqual(download.command.id, test_command)
        with open('test_file.txt', 'w', encoding='utf8') as fp:
            fp.write("New test file created")


class DownloadDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Youtube')
        Download.objects.create(
            command=command,
            source=source,
            url='URL Test',
            title='Title Test',
            active_task_id='a1b2',
            status=Download.Status.COMPLETED,
            file_path='testing.txt'
        )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/1/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(
            reverse('download:detail', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(
            reverse('download:detail', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'download_detail.html')

    def test_view_returns_download_with_correct_status(self):
        response = self.client.get(
            reverse('download:detail', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['download'].id, 1)
        self.assertEqual(
            response.context['download'].status, Download.Status.MISSING)


class DownloadArchiveViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Youtube')
        Download.objects.create(
            command=command,
            source=source,
            url='URL Test',
            title='Title Test',
            active_task_id='a1b2',
            status=Download.Status.COMPLETED
        )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/1/archive/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(
            reverse('download:archive', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(
            reverse('download:archive', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'download_confirm_delete.html')

    def test_view_archives_correctly(self):
        response = self.client.post(
            reverse('download:archive', kwargs={'pk': 1}))
        self.assertRedirects(response, reverse('download:list'))
        download = Download.objects.get(id=1)
        self.assertEqual(download.status, Download.Status.ARCHIVED)


class DownloadCancelViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Youtube')
        Download.objects.create(
            command=command,
            source=source,
            url='URL Test',
            title='Title Test',
            active_task_id='a1b2',
            status=Download.Status.COMPLETED
        )

    @patch("download_ui.apps.download.views.app.control.revoke")
    def test_view_url_exists_at_desired_location(self, _mocked_revoke):
        response = self.client.get('/download/1/cancel/')
        self.assertEqual(response.status_code, 200)

    @patch("download_ui.apps.download.views.app.control.revoke")
    def test_view_url_accessible_by_name(self, _mocked_revoke):
        response = self.client.get(
            reverse('download:cancel', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    @patch("download_ui.apps.download.views.app.control.revoke")
    def test_view_uses_correct_template(self, _mocked_revoke):
        response = self.client.get(
            reverse('download:cancel', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'download_confirm_cancel.html')

    @patch("download_ui.apps.download.views.app.control.revoke")
    def test_view_archives_correctly(self, mocked_revoke):
        response = self.client.post(
            reverse('download:cancel', kwargs={'pk': 1}))
        self.assertRedirects(response, reverse('download:home'))
        download = Download.objects.get(id=1)
        args, kwargs = mocked_revoke.call_args
        self.assertEqual(args[0], download.active_task_id)
        self.assertTrue(kwargs['terminate'])
        self.assertEqual(kwargs['signal'], 'SIGUSR1')
        self.assertEqual(download.status, Download.Status.TERMINATED)


class DownloadListViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # Create 23 downloads for pagination tests
        number_of_downloads = 24

        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Youtube')

        for down_id in range(number_of_downloads):
            Download.objects.create(
                command=command,
                source=source,
                url=f'URL {down_id}',
                title=f'Title {down_id}'
            )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/list/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(reverse('download:list'))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(reverse('download:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'download_list.html')

    def test_pagination_is_twenty(self):
        response = self.client.get(reverse('download:list'))
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['download_list']), 20)

    def test_lists_all_downloads(self):
        # Get second page and confirm it has (exactly) remaining 4 items
        response = self.client.get(reverse('download:list')+'?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('is_paginated' in response.context)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['download_list']), 4)

    def test_search_query_exists(self):
        # Query and get any with title containg a 3 (should be 3 results 3,13,23)
        response = self.client.get(reverse('download:list')+'?q=3')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['download_list']), 3)
        for download in response.context['download_list']:
            self.assertTrue('3' in download.title)


class DownloadProgressViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        command = Command.objects.create(name='YTDL')
        source = Source.objects.create(name='Youtube')
        Download.objects.create(
            command=command,
            source=source,
            url='URL Test',
            title='Title Test',
            active_task_id='a1b2',
            status=Download.Status.COMPLETED
        )

    def test_view_url_exists_at_desired_location(self):
        response = self.client.get('/download/1/progress/')
        self.assertEqual(response.status_code, 200)

    def test_view_url_accessible_by_name(self):
        response = self.client.get(
            reverse('download:progress', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client.get(
            reverse('download:progress', kwargs={'pk': 1}))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'partials/download_progress.html')
        self.assertEqual(response.context['download'].id, 1)
        self.assertEqual(response.context['trigger'], 'none')

    @patch("download_ui.apps.download.views.AsyncResult")
    def test_context_values_status_started_task_started(self, mocked_async_result):
        download_id = 1
        download = Download.objects.get(id=download_id)
        download.status = Download.Status.STARTED
        download.save()
        task_id = 'a1b2'
        task_status = 'STARTED'
        default_task_info = {'percent_str': '0.0%', 'percent': 0.0}
        mocked_async_result.return_value = MagicMock(
            id=task_id, status=task_status)
        response = self.client.get(
            reverse('download:progress', kwargs={'pk': download_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['download'].id, download_id)
        self.assertEqual(response.context['trigger'], 'load delay:600ms')
        self.assertEqual(response.context['task_id'], task_id)
        self.assertEqual(response.context['task_status'], task_status)
        self.assertEqual(response.context['task_info'], default_task_info)

    @patch("download_ui.apps.download.views.AsyncResult")
    def test_context_values_status_started_task_progress(self, mocked_async_result):
        download_id = 1
        download = Download.objects.get(id=download_id)
        download.status = Download.Status.STARTED
        download.save()
        task_id = 'a1b2'
        task_status = 'PROGRESS'
        task_info = {'percent_str': '25.0%', 'percent': 25.0}
        mocked_async_result.return_value = MagicMock(
            id=task_id, status=task_status, info=task_info)
        response = self.client.get(
            reverse('download:progress', kwargs={'pk': download_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['download'].id, download_id)
        self.assertEqual(response.context['trigger'], 'load delay:600ms')
        self.assertEqual(response.context['task_id'], task_id)
        self.assertEqual(response.context['task_status'], task_status)
        self.assertEqual(response.context['task_info'], task_info)

    def test_context_values_status_completed(self):
        download_id = 1
        response = self.client.get(
            reverse('download:progress', kwargs={'pk': download_id}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['download'].id, download_id)
        self.assertEqual(response.context['trigger'], 'none')
