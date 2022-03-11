from abc import abstractmethod, ABC
from collections import namedtuple
from contextlib import redirect_stdout
import io
import json
import logging
import os
import re
import sys

from django.conf import settings
from twitchdl import commands, utils
import youtube_dl

from download_ui.apps.download.exceptions import ExtractionError, DownloadError

logger = logging.getLogger('__name__')


class Downloader(ABC):
    def __init__(self, task=None):
        self.task = task

    @abstractmethod
    def extract(self, url):
        pass

    @abstractmethod
    def download(self, url, code, down_id):
        pass

    @staticmethod
    @abstractmethod
    def format_size(total_bytes):
        return str(total_bytes)

    @staticmethod
    def get_downloader(command, **kwargs):
        downloaders = { down.command : down for down in Downloader.__subclasses__() }
        return downloaders[command](**kwargs)


class YoutubeDownloader(Downloader):
    command = 'YTDL'

    def __init__(self, task=None, code=''):
        Downloader.__init__(self, task)
        self.two_stages = '+bestaudio' in code
        self.first_stage = True
        self.final_filename = None

    def my_hook(self, down):
        if down['status'] == 'finished':
            # If it's a youtube-dl download with separate audio and video
            # Video is downloaded first and then audio
            # We want to keep the filename from the video download
            if self.two_stages and self.first_stage:
                temp_path, ext = os.path.splitext(down['filename'])
                file_sans_ext, _ = os.path.splitext(temp_path)
                self.final_filename = f'{file_sans_ext}{ext}'
                self.first_stage = False
            else:
                filename = down['filename'] if not self.two_stages else self.final_filename
                self.task.update_state(state='FILENAME', meta={
                                       'filename': filename})
                logger.debug("Done downloading %s", filename)

        if down['status'] == 'downloading':
            percent_str = down['_percent_str'].strip()
            percent_float = float(percent_str.strip('%'))

            # youtube-dl prints two separate progress percentages for the video and
            # and audio download. The two have to be joined together
            if self.two_stages:
                percent_float = (percent_float / 2 if self.first_stage
                                 else (percent_float / 2) + 50.0)
                percent_str = f'{round(percent_float, 1)}%'

            percent_int = str(round(percent_float))
            logger.debug("Percent: %s ETA: %s", percent_str, down['_eta_str'])
            self.task.update_state(
                state='PROGRESS',
                meta={'percent_str': percent_str, 'percent': percent_int}
            )

    @staticmethod
    def format_size(total_bytes):
        return youtube_dl.utils.format_bytes(total_bytes)

    @staticmethod
    def get_download_opts(hook, code, down_id):
        ydl_opts = {
            'format': code,
            'outtmpl': os.path.join(
                settings.FILE_PATH_FIELD_DIRECTORY,
                f'%(extractor_key)s/%(title)s-{down_id}-%(resolution)s.%(ext)s'
            ),
            'logger': logger,
            'progress_hooks': [hook],
            'restrictfilenames': True,
            'noplaylist': True,
            'nooverwrites': True
        }
        return ydl_opts

    @staticmethod
    def get_extract_opts():
        ydl_opts = {
            'logger': logger
        }
        return ydl_opts

    @staticmethod
    def parse_extraction(result):
        if not result:
            raise ExtractionError(
                'youtube-dl', 'Download Information not found')

        format_info = []
        audio_exists = False

        for format_junk in result['formats']:
            res = None
            code = None
            # Flip the boolean if audio only files are found but ignore them
            if format_junk.get('vcodec') == 'none':
                if format_junk.get('acodec') != 'none':
                    audio_exists = True
                continue
            # If there are audio files, we only care about video only, if there
            # are no audio files, we need combined files
            if audio_exists:
                if format_junk.get('acodec') != 'none':
                    continue
            else:
                if format_junk.get('acodec') == 'none':
                    continue
            # Get the resolution string (cribbed from youtube-dl's formatting)
            if format_junk.get('resolution') is not None:
                res = format_junk['resolution']
            elif format_junk.get('height') is not None:
                if format_junk.get('width') is not None:
                    res = f'{format_junk["width"]}x{format_junk["height"]}'
                else:
                    res = f'{format_junk["height"]}p'
            elif format_junk.get('width') is not None:
                res = f'{format_junk["width"]}x?'
            else:
                continue

            # form code for formatting
            # Always using best quality audio
            if audio_exists:
                format_id = format_junk['format_id']
                code = f'{format_id}+bestaudio'
            else:
                code = format_junk['format_id']
            format_info.append((format_junk['ext'], res, code))

        results = {
            'channel_name': result['channel'],
            'title': result['title'],
            'slug_id': result['id'],
            'source': result['extractor_key'],
            'format_info': format_info
        }
        return results

    def extract(self, url):
        ydl = youtube_dl.YoutubeDL(self.get_extract_opts())
        try:
            with ydl:
                result = ydl.extract_info(
                    url,
                    download=False  # We just want to extract the info
                )

        except Exception as error:
            _, exc_value, _ = sys.exc_info()
            raise ExtractionError(
                'youtube-dl', exc_value.exc_info[1]) from error

        return self.parse_extraction(result)

    def download(self, url, code, down_id):
        ydl = youtube_dl.YoutubeDL(
            self.get_download_opts(self.my_hook, code, down_id))
        try:
            with ydl:
                result = ydl.download([url])
            return result
        except Exception as error:
            _, exc_value, _ = sys.exc_info()
            raise DownloadError('youtube-dl', exc_value.exc_info[1]) from error


class TwitchDownloader(Downloader):
    command = 'TWDL'

    def __init__(self, task=None, code=''):
        Downloader.__init__(self, task)
        self.code = code

    @staticmethod
    def format_size(total_bytes):
        return utils.format_size(total_bytes)

    @staticmethod
    def get_download_opts(url, code, down_id):
        options = namedtuple(
            'Options', ['video', 'output', 'quality', 'overwrite'])
        options.video = url
        options.output = os.path.join(settings.FILE_PATH_FIELD_DIRECTORY,
                                      f'twitch/{{title_slug}}-{down_id}-{code}.{{format}}')
        options.quality = code
        options.overwrite = False
        return options

    @staticmethod
    def get_extract_opts(url):
        options = namedtuple('Options', ['identifier', 'json'])
        options.identifier = url
        options.json = True
        return options

    @staticmethod
    def parse_extraction(result):
        if not result:
            raise ExtractionError(
                'twitch-dl', 'Download Information not found')
        # determine whether clip or video
        if 'slug' in result:  # it's a clip
            identifier = result['slug']
            channel = result['broadcaster']
            format_info = []
            for format_junk in result['videoQualities']:
                res = format_junk['quality']
                code = res
                url = format_junk['sourceURL']
                _, ext = os.path.splitext(url)
                ext = ext.lstrip(".")
                format_info.append((ext, res, code))
        else:
            identifier = result['id']
            channel = result['creator']
            format_info = []
            for format_junk in result['playlists']:
                res = format_junk['video']
                code = res
                ext = 'mkv'
                format_info.append((ext, res, code))

        results = {
            'channel_name': channel['displayName'],
            'title': result['title'],
            'slug_id': identifier,
            'source': 'Twitch',
            'format_info': format_info
        }
        return results

    def extract(self, url):
        try:
            with redirect_stdout(io.StringIO()) as string_obj:
                commands.info(self.get_extract_opts(url))
            std_out = string_obj.getvalue()
            json_content = json.loads(std_out)
        except Exception as error:
            raise ExtractionError('twitch-dl', str(error)) from error

        return self.parse_extraction(json_content)

    def download(self, url, code, down_id):
        try:
            with redirect_stdout(io.StringIO()) as string_obj:
                commands.download(self.get_download_opts(url, code, down_id))
            std_out = string_obj.getvalue()
            matches = re.findall(r'Downloaded: (\S*)', std_out)
            filename_raw = matches[-1]
            ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
            filename = ansi_escape.sub('', filename_raw)
            logger.debug('Parsed filename as %s', filename)
            self.task.update_state(state='FILENAME', meta={
                                   'filename': filename})
        except Exception as error:
            raise DownloadError('twitch-dl', str(error)) from error
