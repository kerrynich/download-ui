from __future__ import absolute_import
import logging
import os

from celery import shared_task

from .downloaders.downloader import TwitchDownloader, YoutubeDownloader
from .exceptions import DownloadError
from .models import Download

logger = logging.getLogger('__name__')


@shared_task(bind=True)
def worker_download(self, url, download_id, command, code):

    download = Download.objects.get(pk=download_id)
    status = Download.Status.COMPLETED
    filepath = 'N/A'
    size = 'N/A'

    download.active_task_id = self.request.id
    download.save()

    downloader = (YoutubeDownloader(task=self, code=code) if command == 'YTDL'
                  else TwitchDownloader(task=self))
    try:
        downloader.download(url, code, download_id)
        logger.debug('Downloading complete')
    except (DownloadError) as error:
        status = Download.Status.FAILED
        logger.error(error)

    result = self.AsyncResult(self.request.id)

    try:
        if status == Download.Status.COMPLETED:
            filepath = result.info['filename']
            size = downloader.format_size(
                os.path.getsize(filepath))

    except (OSError) as error:
        status = Download.Status.FAILED
        logger.error(error)

    download.file_path = filepath
    download.size = size
    download.status = status
    download.save()
    logger.debug('Task complete with status: %s', status.label)
