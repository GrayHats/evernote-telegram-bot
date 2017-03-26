import asyncio
import hashlib
import time
import logging
import re
from os.path import basename
from concurrent.futures import ThreadPoolExecutor

import evernote.edam.type.ttypes as Types
import evernote.edam.error.ttypes as ErrorTypes
from ext.evernote import EvernoteSdk


class EvernoteApiError(Exception):
    def __init__(self, description=''):
        super(EvernoteApiError, self).__init__(description)


class NoteNotFound(EvernoteApiError):
    pass


class RateLimitReached(EvernoteApiError):
    pass


class PermissionDenied(EvernoteApiError):
    pass


class TokenExpired(EvernoteApiError):
    pass


class ExceptionInfo:

    def __init__(self, exc_type, message=None):
        self.exc_type = exc_type
        self.message = message


def edam_user_exception(func):
    def _wrap():
        try:
            return func()
        except ErrorTypes.EDAMUserException as e:
            if e.errorCode == 3:
                message = 'Token is invalid (or has no permissions)'
                exc_info = ExceptionInfo(PermissionDenied, message)
            elif e.errorCode == 9:
                message = 'Evernote access token is expired'
                exc_info = ExceptionInfo(TokenExpired, message)
            else:
                message = 'Error code = {0}, parameter = {1}'.format(
                    e.errorCode, e.parameter
                )
                exc_info = ExceptionInfo(EvernoteApiError, message)
        raise exc_info.exc_type(exc_info.message)
    return _wrap


class NoteContent:

    def __init__(self, note=None):
        self.content_objects = []
        self._old_content = ''
        self._old_resources = []
        if note is not None:
            self._old_resources = note.resources or []
            self._old_content = self._parse_content(note.content)
        self._new_content = ''

    def _parse_content(self, xml_content):
        m = re.search(r'<en-note>(?P<content>.*)</en-note>', xml_content or '')
        if m:
            return m.group('content')
        return ''

    def add_file(self, path, mime_type):
        resource, hexdigest = self._make_resource(path, mime_type)
        self.content_objects.append({
                'type': 'file',
                'path': path,
                'mime_type': mime_type,
                'resource': resource,
                'hexdigest': hexdigest,
            })

    def add_text(self, text):
        if text:
            self.content_objects.append({
                    'type': 'string',
                    'value': text,
                })

    def _make_resource(self, filename, mime_type):
        with open(filename, 'rb') as f:
            data_bytes = f.read()
            md5 = hashlib.md5()
            md5.update(data_bytes)

            data = Types.Data()
            data.size = len(data_bytes)
            data.bodyHash = md5.digest()
            data.body = data_bytes

            resource = Types.Resource()
            resource.mime = mime_type
            resource.data = data
            short_name = basename(filename)
            resource.attributes = Types.ResourceAttributes(fileName=short_name)
        return resource, md5.hexdigest()

    def get_resources(self):
        resources = [r for r in self._old_resources]
        for entry in self.content_objects:
            if entry['type'] == 'file':
                resources.append(entry['resource'])
        return resources

    def __str__(self):
        new_content = ''
        for entry in self.content_objects:
            content_entry = ''
            if entry['type'] == 'file':
                content_entry = '<br />\
<en-media type="{mime_type}" hash="{md5}" />'.format(
                    mime_type=entry['mime_type'],
                    md5=entry['hexdigest']
                )
            elif entry['type'] == 'string':
                content_entry = '<br />{text}'.format(
                    text=entry['value'].replace('&', '&amp;')
                )
            new_content += content_entry

        return '\
<?xml version="1.0" encoding="UTF-8"?>\
<!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">\
<en-note>{old_content}<br />{new_content}</en-note>'.format(
                old_content=self._old_content,
                new_content=new_content
            )


class AsyncEvernoteApi:

    def __init__(self, loop=None, sandbox=False):
        self.loop = loop or asyncio.get_event_loop()
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.sandbox = sandbox
        self.logger = logging.getLogger('evernote_api')

    def __call_store_method(self, method_name, auth_token, *args, **kwargs):
        try:
            start_time = time.time()
            self.logger.debug("Start call '{0}'".format(method_name))
            sdk = EvernoteSdk(token=auth_token, sandbox=self.sandbox)
            note_store = sdk.get_note_store()
            method = getattr(note_store, method_name)
            result = method(*args, **kwargs)
            self.logger.debug("Finish call '{0}' in {1} sec".format(method_name, time.time() - start_time))
            return result
        except ErrorTypes.EDAMNotFoundException:
            exc_info = ExceptionInfo(NoteNotFound, 'Note not found')
        except ErrorTypes.EDAMUserException as e:
            if e.errorCode == 3:
                exc_info = ExceptionInfo(PermissionDenied, 'It seems that token is invalid (or has no permissions)')
            elif e.errorCode == 9:
                exc_info = ExceptionInfo(TokenExpired, 'Evernote access token is expired')
            else:
                exc_info = ExceptionInfo(EvernoteApiError, 'Error code = {0}, parameter = {1}'.format(e.errorCode, e.parameter))
        except ErrorTypes.EDAMSystemException as e:
            if e.errorCode == 19 and hasattr(e, 'rateLimitDuration'):
                exc_info = ExceptionInfo(RateLimitReached, 'rateLimitDuration == {0}'.format(e.rateLimitDuration))
            else:
                exc_info = ExceptionInfo(EvernoteApiError, "{0}: {1}".format(getattr(e, 'errorCode', ''), getattr(e, 'message', '')))
        except Exception as e:
            self.logger.error(e)
            raise EvernoteApiError('Evernote API error') from None

        raise exc_info.exc_type(exc_info.message)

    async def get_user(self, auth_token):
        def get_info(auth_token):
            sdk = EvernoteSdk(token=auth_token, sandbox=self.sandbox)
            user_store = sdk.get_user_store()
            user = user_store.getUser(auth_token)
            return user

        return await self.loop.run_in_executor(self.executor, get_info, auth_token)

    async def get_service_host(self, auth_token):
        sdk = EvernoteSdk(token=auth_token, sandbox=self.sandbox)
        return sdk.service_host

    async def get_note_link(self, auth_token, note_guid, app_link=False):
        user = await self.get_user(auth_token)
        app_link_template = 'evernote:///view/{user_id}/{shard}/{note_guid}/{note_guid}/'
        web_link_template = 'https://{service}/shard/{shard}/nl/{user_id}/{note_guid}/'
        params = {
            'service': await self.get_service_host(auth_token),
            'shard': user.shardId,
            'user_id': user.id,
            'note_guid': note_guid,
        }
        if app_link:
            return app_link_template.format(**params)
        return web_link_template.format(**params)

    async def get_note(self, auth_token, note_guid):
        def fetch(note_guid):
            return self.__call_store_method('getNote', auth_token, note_guid, True, True, False, False) # TODO: по идее можно соптимизировать и не запрашивать информацию о ресурсах когда она не нужна

        result = await self.loop.run_in_executor(self.executor, fetch, note_guid)
        self.logger.debug('Note fetched.')
        return result

    async def save_note(self, auth_token, note):
        def save(note):
            return self.__call_store_method('createNote', auth_token, note)

        result = await self.loop.run_in_executor(self.executor, save, note)
        self.logger.debug('Note saved.')
        return result

    async def new_note(self, auth_token, notebook_guid, text,
                       title=None, files=None):
        def create():
            note = Types.Note()
            note_title = title or ('%s...' % text[:25] if len(text) > 30 else text)
            note_title = note_title.replace('\n', ' ')
            note_title = note_title.replace('\r', ' ')
            note.title = note_title.strip()
            note.notebookGuid = notebook_guid
            content = NoteContent(note)
            content.add_text(text)
            if files:
                for path, mime_type in files:
                    content.add_file(path, mime_type)
            note.resources = content.get_resources()
            note.content = str(content)
            return self.__call_store_method('createNote', auth_token, note)

        note = await self.loop.run_in_executor(self.executor, create)
        self.logger.debug('Note created.')
        return note.guid

    async def update_note(self, auth_token, note):
        def update(note):
            return self.__call_store_method('updateNote', auth_token, note)

        result = await self.loop.run_in_executor(self.executor, update, note)
        self.logger.debug('Note updated.')
        return result

    async def get_default_notebook(self, auth_token):
        def get_nb():
            return self.__call_store_method('getDefaultNotebook', auth_token)

        return await self.loop.run_in_executor(self.executor, get_nb)

    async def get_oauth_data(self, user_id, api_key, api_secret, oauth_callback, session_key):
        def _get_oauth_data():
            sdk = EvernoteSdk(consumer_key=api_key, consumer_secret=api_secret, sandbox=self.sandbox)
            bytes_key = ('%s%s%s' % (api_key, api_secret, user_id)).encode()
            callback_key = hashlib.sha1(bytes_key).hexdigest()
            callback_url = "%(callback_url)s?key=%(key)s&session_key=%(session_key)s" % {
                'callback_url': oauth_callback,
                'key': callback_key,
                'session_key': session_key,
            }
            request_token = sdk.get_request_token(callback_url)
            oauth_url = sdk.get_authorize_url(request_token)
            return {
                'oauth_url': oauth_url,
                'oauth_token': request_token['oauth_token'],
                'oauth_token_secret': request_token['oauth_token_secret'],
                'callback_key': callback_key
            }

        return await self.loop.run_in_executor(self.executor, _get_oauth_data)

    async def get_access_token(self, api_key, api_secret, oauth_token, oauth_token_secret, oauth_verifier):
        def _get_access_token():
            sdk = EvernoteSdk(consumer_key=api_key, consumer_secret=api_secret, sandbox=self.sandbox)
            return sdk.get_access_token(oauth_token, oauth_token_secret, oauth_verifier)

        return await self.loop.run_in_executor(self.executor, _get_access_token)

    async def list_notebooks(self, auth_token):
        @edam_user_exception
        def _list_notebooks():
            sdk = EvernoteSdk(token=auth_token, sandbox=self.sandbox)
            note_store = sdk.get_note_store()
            return note_store.listNotebooks()

        return await self.loop.run_in_executor(self.executor, _list_notebooks)
