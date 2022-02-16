import logging
import os

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _get

from .downloaders.downloader import TwitchDownloader, YoutubeDownloader
from .exceptions import ExtractionError

logger = logging.getLogger('__name__')


class TimestampedModel(models.Model):
    # A timestamp representing when this object was created.
    created_at = models.DateTimeField(auto_now_add=True)

    # A timestamp reprensenting when this object was last updated.
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

        # By default, any model that inherits from `TimestampedModel` should
        # be ordered in reverse-chronological order. We can override this on a
        # per-model basis as needed, but reverse-chronological is a good
        # default ordering for most models.
        ordering = ['-created_at', '-updated_at']


class Command(TimestampedModel):
    class CommandName(models.TextChoices):
        YOUTUBEDL = 'YTDL', _get('youtube-dl')
        TWITCHDL = 'TWDL', _get('twitch-dl')

    name = models.CharField(
        max_length=4,
        choices=CommandName.choices,
        default=CommandName.TWITCHDL,
    )

    def __str__(self):
        return self.get_name_display()


class Source(TimestampedModel):
    name = models.CharField(unique=True, max_length=100)

    def __str__(self):
        return self.name


class Quality(TimestampedModel):
    name = models.CharField(unique=True, max_length=100)

    def __str__(self):
        return self.name


class Extension(TimestampedModel):
    name = models.CharField(unique=True, max_length=50)
    qualities = models.ManyToManyField(Quality, through='Format')

    def __str__(self):
        return self.name


class Format(models.Model):
    quality = models.ForeignKey(Quality, on_delete=models.CASCADE)
    extension = models.ForeignKey(Extension, on_delete=models.CASCADE)
    command = models.ForeignKey(Command, on_delete=models.CASCADE)
    format_code = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.extension.name} : {self.quality.name}'


class Download(TimestampedModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.downloader = None
        self.format_ids = []

    class Status(models.TextChoices):
        DRAFT = 'D', _get('Draft')
        STARTED = 'S', _get('Started')
        FAILED = 'F', _get('Failed')
        COMPLETED = 'C', _get('Completed')
        ARCHIVED = 'A', _get('Archived')
        MISSING = 'M', _get('Missing')

    # The command used to download
    command = models.ForeignKey(Command, on_delete=models.CASCADE)

    # The website to download from
    source = models.ForeignKey(Source, on_delete=models.CASCADE)

    # The URL to download
    url = models.URLField(max_length=300)

    # The file location of the download
    file_path = models.FilePathField(
        path=settings.FILE_PATH_FIELD_DIRECTORY,
        max_length=300,
        allow_files=True,
        allow_folders=False)

    # The name of the video
    title = models.CharField(max_length=200)

    # The Source's ID
    slug_id = models.CharField(max_length=100)

    # The Source's Channel name
    channel_name = models.CharField(max_length=100)

    # Filesize as a string
    size = models.CharField(max_length=25)

    # Whether download job is done
    status = models.CharField(
        max_length=1,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # The active task id for the celery task performing the download
    active_task_id = models.CharField(max_length=200)

    # The possible format options for this download
    choices_for = models.ManyToManyField(Format, related_name='choices')

    # The selected format for the final download
    file_format = models.ForeignKey(
        Format, on_delete=models.CASCADE, blank=True, null=True)

    def get_absolute_url(self):
        return reverse('download:detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.title

    def set_missing_if_file_not_found(self):
        if not os.path.exists(self.file_path) and self.status == Download.Status.COMPLETED:
            self.status = Download.Status.MISSING

    def archive_download(self):
        if os.path.exists(self.file_path):
            os.remove(self.file_path)

        self.status = Download.Status.ARCHIVED

    def clean_fields(self, exclude=None):
        super().clean_fields(exclude=exclude)
        logger.debug('Cleaning fields')
        command = self.command
        url = self.url

        # Only do something if both fields are valid so far.
        # Also only if the download object is being created for the first time
        if (not self.id) and command and url:

            self.downloader = YoutubeDownloader() if command.name == 'YTDL' else TwitchDownloader()
            try:
                result = self.downloader.extract(url)
            except ExtractionError as error:
                raise ValidationError(
                    _get('Download failure: %(message)s'),
                    code='invalid',
                    params={'message': error.message},
                ) from error

            # Add attributes parsed from info extraction
            self.source, _ = Source.objects.get_or_create(
                name=result['source'])
            self.title = result['title']
            self.slug_id = result['slug_id']
            self.channel_name = result['channel_name']

            # Create database objects for Video formats if they don't exist
            for (ext, qual, code) in result['format_info']:
                extension, _ = Extension.objects.get_or_create(name=ext)
                quality, _ = Quality.objects.get_or_create(name=qual)
                comm = Command.objects.get(name=self.command.name)
                file_format, _ = Format.objects.get_or_create(
                    quality=quality,
                    extension=extension,
                    defaults={'format_code': code, 'command': comm}
                )
                self.format_ids.append(file_format.id)
                logger.debug(
                    'File format option: Ext: %s Res: %s Code: %s', ext, qual, code)

            logger.debug('Finished cleaning fields')

    def save(self, *args, **kwargs):
        not_exists = not self.id
        format_ids = self.format_ids

        # Call the "real" save() method.
        super().save(*args, **kwargs)

        # Add the relationships to the format objects after object is saved
        if not_exists:
            self.choices_for.add(*format_ids)
