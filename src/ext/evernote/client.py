from typing import List

import aiomcache

from ext.evernote.api import AsyncEvernoteApi
from ext.evernote.api import NoteNotFound
from ext.evernote.api import NoteContent


class Evernote:

    def __init__(self, sandbox=False):
        self.__api = AsyncEvernoteApi(sandbox=sandbox)
        self.cache = aiomcache.Client('127.0.0.1', 11211)  # TODO:

    async def get_note(self, token, guid):
        return await self.__api.get_note(token, guid)

    async def create_note(self, token, title, text,
                          notebook_guid, files: List):
        if text:
            title = ('%s...' % text[:15] if len(text) > 15 else text)
        title = '[BOT] {0}'.format(title)
        return await self.__api.new_note(token, notebook_guid, text,
                                         title, files)

    async def update_note(self, token, note_guid, notebook_guid,
                          text, files: List, *, request_type=None):
        try:
            note = await self.__api.get_note(token, note_guid)
        except NoteNotFound:
            self.logger.warning(
                'Note {0} not found. Creating new note'.format(note_guid)
            )
            note = await self.__api.new_note(token, notebook_guid, text,
                                             '[TELEGRAM BOT]', files)
        content = NoteContent(note)
        content.add_text(text)
        if files:
            note = await self.__api.new_note(token, notebook_guid, text,
                                             '[Files]', files)
            user = await self.__api.get_user(token)
            note_url = 'https://{host}/shard/{shard}/nl/{uid}/{guid}/'.format(
                host=await self.__api.get_service_host(token),
                shard=user.shardId,
                uid=user.id,
                guid=note.guid
            )
            html = '{file_type}: <a href="{url}">{url}</a>'.format(
                file_type=request_type.capitalize(),
                url=note_url
            )
            content.add_text(html)

        note.content = str(content)
        await self.__api.update_note(token, note)
