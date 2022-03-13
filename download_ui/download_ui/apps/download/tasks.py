from __future__ import absolute_import
import logging
import os

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from celery.schedules import crontab

from download_ui.celery import app
from .downloaders.downloader import Downloader
from .exceptions import DownloadError
from .models import Download

logger = logging.getLogger('__name__')


@shared_task(bind=True)
def worker_download(self, download_id):
    filepath = 'N/A'
    size = 'N/A'
    result = None
    download = Download.objects.get(pk=download_id)
    download.active_task_id = self.request.id
    download.save()

    try:
        status = Download.Status.COMPLETED
        url = download.url
        command = download.command.name
        code = download.file_format.format_code

        downloader = Downloader.get_downloader(command, task=self, code=code)
        try:
            downloader.download(url, code, download_id)
            logger.debug('Downloading complete')
        except (DownloadError) as error:
            status = Download.Status.FAILED
            logger.error(error)

        result = self.AsyncResult(self.request.id)

        if status == Download.Status.COMPLETED:
            filepath = result.info['filename']
            try:
                size = downloader.format_size(os.path.getsize(filepath))

            except (OSError) as error:
                status = Download.Status.FAILED
                logger.error(error)
    except SoftTimeLimitExceeded:
        logger.info('Task %s for download %d Terminated', self.request.id, download_id)
        status = Download.Status.TERMINATED
    finally:
        download.file_path = filepath
        download.size = size
        download.status = status
        download.save()
        logger.debug('Task complete with status: %s', status.label)

@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    # Executes every morning at 3:30 a.m.
    sender.add_periodic_task(
        crontab(hour=3, minute=30),
        check_for_missing_files.s(),
    )

@app.task
def check_for_missing_files():
    completed_downloads = Download.objects.filter(status=Download.Status.COMPLETED)
    for download in completed_downloads:
        download.set_missing_if_file_not_found()
        download.save()
