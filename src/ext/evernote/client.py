import logging
from typing import List

import aiomcache

from ext.evernote.api import AsyncEvernoteApi
from ext.evernote.api import NoteNotFound
from ext.evernote.api import NoteContent


class Evernote:

    def __init__(self, sandbox=False, *, title_prefix=None):
        self.api = AsyncEvernoteApi(sandbox=sandbox)
        self.cache = aiomcache.Client('127.0.0.1', 11211)  # TODO:
        self.title_prefix = title_prefix or ''
        self.logger = logging.getLogger()

    async def get_note(self, token, guid):
        return await self.api.get_note(token, guid)

    async def create_note(self, token, title, text,
                          notebook_guid, files: List=None):
        '''
        Returns GUID for new note
        '''
        if text:
            title = '%s...' % text[:15] if len(text) > 15 else text
        title = '{0} {1}'.format(self.title_prefix, title)
        return await self.api.new_note(token, notebook_guid, text,
                                       title, files)

    async def update_note(self, token, note_guid, notebook_guid,
                          text, files: List=None, *, request_type=None):
        try:
            note = await self.api.get_note(token, note_guid)
        except NoteNotFound:
            self.logger.warning(
                'Note {0} not found. Creating new note'.format(note_guid)
            )
            note_guid = await self.api.new_note(token, notebook_guid, '',
                                                self.title_prefix, files)
            note = await self.api.get_note(token, note_guid)
        content = NoteContent(note)
        content.add_text(text)
        if files:
            # Separate note for files
            note_guid = await self.api.new_note(token, notebook_guid, '',
                                                '[Files]', files)
            user = await self.api.get_user(token)
            note_url = 'https://{host}/shard/{shard}/nl/{uid}/{guid}/'.format(
                host=await self.api.get_service_host(token),
                shard=user.shardId,
                uid=user.id,
                guid=note_guid
            )
            file_type = request_type.capitalize() if request_type else 'File'
            html = '{file_type}: <a href="{url}">{url}</a>'.format(
                file_type=file_type, url=note_url
            )
            content.add_text(html)

        note.content = str(content)
        await self.api.update_note(token, note)

    def __filter(self, entries, query):
        if not query:
            return entries
        result = []
        for entry in entries:
            for k, v in query.items():
                if entry[k] != v:
                    break
            else:
                result.append(entry)
        return result

    async def list_notebooks(self, token, query=None):
        notebooks = await self.api.list_notebooks(token)
        notebooks = [{'guid': nb.guid, 'name': nb.name} for nb in notebooks]
        return self.__filter(notebooks, query)

    async def get_note_link(self, token, note_guid):
        return await self.api.get_note_link(token, note_guid)

    async def get_access_token(self, config, oauth_data, oauth_verifier):
        return await self.api.get_access_token(
            config['key'],
            config['secret'],
            oauth_data['oauth_token'],
            oauth_data['oauth_token_secret'],
            oauth_verifier
        )

    async def get_default_notebook(self, token):
        return await self.api.get_default_notebook(token)

    async def get_oauth_data(self, user_id, config, session_key):
        return await self.api.get_oauth_data(
            user_id, config['key'], config['secret'], config['oauth_callback'],
            session_key
        )
