from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.urls import reverse

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

class Source(TimestampedModel):

    class SourceName(models.TextChoices):
        YOUTUBE = 'YT', _('YouTube')
        TWITCH = 'TW', _('Twitch')

    class CommandName(models.TextChoices):
        YOUTUBEDL = 'YTDL', _('youtube-dl')
        TWITCHDL = 'TWDL', _('twitch-dl')

    # The website to download from
    source = models.CharField(
        max_length=2,
        choices=SourceName.choices,
        default=SourceName.TWITCH,
    )

    # The command used to download
    command = models.CharField(
        max_length=4,
        choices=CommandName.choices,
        default=CommandName.TWITCHDL,
    )

    def __str__(self):
        return self.source

class Download(TimestampedModel):

    # The webiste the download came from
    source = models.ForeignKey(Source, on_delete=models.PROTECT)

    # The file location of the download
    file_path = models.FilePathField(
        path=settings.FILE_PATH_FIELD_DIRECTORY,
        max_length=300,
        allow_files=True,
        allow_folders=False)

    # The URL to download
    url = models.URLField(max_length=300)

    # The name of the video
    title = models.CharField(max_length=100)

    def get_absolute_url(self):
        return reverse('download-detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.title
