import os
import traceback
import time

from config import config
from ext.telegram.bot import TelegramBotError
from utils.logs import get_logger
from utils.downloader import HttpDownloader
from bot.model import TelegramUpdate
from bot.model import FailedUpdate
from bot.model import User
from ext.telegram.models import Message
from ext.evernote.client import Evernote
from ext.evernote.api import TokenExpired
from ext.telegram.api import BotApi


class TelegramDownloader(HttpDownloader):

    def __init__(self, bot_token, download_dir=None, *, loop=None):
        logger = get_logger('downloader')
        super().__init__(download_dir, logger=logger, loop=loop)
        self.telegram_api = BotApi(bot_token)

    async def download_file(self, file_id):
        url = await self.telegram_api.getFile(file_id)
        destination_file = os.path.join(self.download_dir, file_id)
        response = await self.async_download_file(url, destination_file)
        if url.endswith('.jpg') or url.endswith('.jpeg'):
            mime_type = 'image/jpeg'
        elif url.endswith('.png'):
            mime_type = 'image/png'
        else:
            mime_type = response.headers.get(
                'CONTENT-TYPE',
                'application/octet-stream'
            )
        return (destination_file, mime_type)


class BaseHandler:

    def __init__(self):
        self.logger = get_logger('bot')
        self.evernote = Evernote(title_prefix='[TELEGRAM BOT]')
        self.telegram = BotApi(config['telegram']['token'])

    async def execute(self, user: User, **kwargs):
        chat_id = user.telegram_chat_id
        status_message_id = kwargs['status_message_id']
        request_type = kwargs['request_type']
        message = kwargs['message']
        start_ts = time.time()
        try:
            await self.save_to_evernote(user, request_type, message)
            duration = time.time() - start_ts
            text = '✅ {0} saved ({1:.2} s)'.format(request_type.capitalize(), duration)
            await self.telegram.editMessageText(chat_id, status_message_id, text)
        except TokenExpired:
            raise TelegramBotError('⛔️ Evernote access token is expired. Send /start to get new token')
        except Exception as e:
            error_text = e.message if hasattr(e, 'message') else 'Something went wrong'
            raise TelegramBotError('❌ {}. Please, try again'.format(error_text))

    async def get_files(self, message: Message):
        return []

    async def get_text(self, message: Message):
        return message.text or message.caption or ''

    async def save_to_evernote(self, user, request_type, message):
        if user.mode == 'one_note':
            await self._update_note(user, request_type, message)
        elif user.mode == 'multiple_notes':
            await self._create_note(user, request_type, message)
        else:
            self.logger.warn('User {0} has invalid mode {1}'.format(user.id, user.mode))
            user.mode = 'multiple_notes'
            user.save()
            await self._create_note(user, request_type, message)

    async def _create_note(self, user: User, request_type: str, message: Message):
        title = request_type.capitalize()
        text = await self.get_text(message)
        files = await self.get_files(message)
        await self.evernote.create_note(
            user.evernote_access_token,
            title,
            text,
            user.current_notebook['guid'],
            files
        )

    async def _update_note(self, user: User, request_type: str, message: Message):
        notebook_guid = user.current_notebook['guid']
        note_guid = user.places.get(notebook_guid)
        if not note_guid:
            error = 'Default note in notebook {0} not exists'.format(
                user.current_notebook['name']
            )
            raise Exception(error)

        text = await self.get_text(message)
        files = await self.get_files(message)
        await self.evernote.update_note(
            user.evernote_access_token,
            note_guid,
            notebook_guid,
            text,
            files,
            request_type=request_type
        )

    async def cleanup(self, user: User, update: TelegramUpdate):
        update.delete()


class FileHandler(BaseHandler):

    def __init__(self):
        super().__init__()
        token = config['telegram']['token']
        downloads_dir = config['downloads_dir']
        self.downloader = TelegramDownloader(token, downloads_dir)

    async def get_files(self, message: Message):
        file_id = self.get_file_id(message)
        file_path, mime_type = await self.downloader.download_file(file_id)
        if hasattr(message, 'document'):
            destination_file = os.path.join(os.path.dirname(file_path), message.document.file_name)
        else:
            destination_file = file_path
        os.rename(file_path, destination_file)
        return [(destination_file, mime_type)]

    def get_file_id(self, message: Message):
        pass

    async def cleanup(self, user: User, update: TelegramUpdate):
        try:
            file_id = self.get_file_id(Message(update.message))
            filename = os.path.join(self.downloader.download_dir, file_id)
            if os.path.exists(filename):
                os.unlink(filename)
            wav_file = "{0}.wav".format(filename)
            if os.path.exists(wav_file):
                os.unlink(wav_file)
        except Exception as e:
            message = '{classname} cleanup failed: {error}'.format(
                classname=self.__class__.__name__, error=e)
            self.logger.fatal(message, exc_info=1)
        await super().cleanup(user, update)


class TextHandler(BaseHandler):
    pass


class PhotoHandler(FileHandler):

    def get_file_id(self, message: Message):
        files = sorted(message.photos, key=lambda x: x.file_size, reverse=True)
        return files[0].file_id


class DocumentHandler(FileHandler):

    def get_file_id(self, message: Message):
        return message.document.file_id


class VideoHandler(FileHandler):

    def get_file_id(self, message: Message):
        return message.video.file_id


class VoiceHandler(FileHandler):

    def get_file_id(self, message: Message):
        return message.voice.file_id

    async def get_files(self, message: Message):
        file_id = self.get_file_id(message)
        ogg_file_path, mime_type = await self.downloader.download_file(file_id)
        mime_type = 'audio/wav'
        wav_filename = "{0}.wav".format(ogg_file_path)
        try:
            # convert to wav
            os.system('opusdec %s %s' % (ogg_file_path, wav_filename))
        except Exception:
            self.logger.error(
                "Can't convert ogg to wav, %s" % traceback.format_exc()
            )
            wav_filename = ogg_file_path
            mime_type = 'audio/ogg'

        return [(wav_filename, mime_type)]


class LocationHandler(BaseHandler):

    async def get_text(self, message: Message):
        latitude = message.location.latitude
        longitude = message.location.longitude
        maps_url = "https://maps.google.com/maps?q=%(lat)f,%(lng)f" % {
            'lat': latitude,
            'lng': longitude,
        }
        title = 'Location'
        text = "<a href='%(url)s'>%(url)s</a>" % {'url': maps_url}

        if hasattr(message, 'venue'):
            venue = message.venue
            address = venue.address
            title = venue.title
            text = "%(title)s<br />%(address)s<br />\
                <a href='%(url)s'>%(url)s</a>" % {
                'title': title,
                'address': address,
                'url': maps_url
            }
            foursquare_id = venue.foursquare_id
            if foursquare_id:
                url = "https://foursquare.com/v/%s" % foursquare_id
                text += "<br /><a href='%(url)s'>%(url)s</a>" % {'url': url}
        return text
