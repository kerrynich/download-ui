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
    download.active_task_id = self.request.id
    download.save()
    downloader = (YoutubeDownloader(task=self, code=code) if command == 'YTDL'
                  else TwitchDownloader(task=self))
    status = Download.Status.COMPLETED
    try:
        downloader.download(url, code)
        logger.debug('Downloading complete')
    except DownloadError as error:
        status = Download.Status.FAILED
        logger.error(error)
    download = Download.objects.get(pk=download_id)
    result = self.AsyncResult(self.request.id)
    if status == Download.Status.COMPLETED:
        download.file_path = result.info['filename']
        download.size = downloader.format_size(os.path.getsize(download.file_path))
    else:
        download.file_path = 'N/A'
        download.size = 'N/A'
    download.status = status
    download.save()
    logger.debug('Task complete')
