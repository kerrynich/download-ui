from __future__ import absolute_import
import logging
import os

from celery import shared_task

from .downloaders.downloader import Downloader
from .exceptions import DownloadError
from .models import Download

logger = logging.getLogger('__name__')


@shared_task(bind=True)
def worker_download(self, download_id):

    download = Download.objects.get(pk=download_id)
    status = Download.Status.COMPLETED
    filepath = 'N/A'
    size = 'N/A'

    download.active_task_id = self.request.id
    download.save()

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

    download.file_path = filepath
    download.size = size
    download.status = status
    download.save()
    logger.debug('Task complete with status: %s', status.label)
