import asyncio
import pytest
import datetime
import random
import os

from conftest import AsyncMock
from bot import EvernoteBot
from bot.dealer import EvernoteDealer
from bot.message_handlers import VoiceHandler


@pytest.mark.async_test
async def test_save_voice_multiple_notes_mode(user):
    user.mode = 'multiple_notes'
    user.save()

    file_id = str(random.randint(1, 10000))
    update_data = {
        'update_id': 93710840,
        'message': {
            'date': datetime.datetime.now(),
            'from': {
                'username': user.username,
                'id': user.id,
            },
            'chat': {
                'id': user.telegram_chat_id,
                'type': 'private',
                'username': user.username,
            },
            'message_id': 164,
            'text': '',
            'voice': {
                'file_size': 12345,
                'file_id': file_id,
                'duration': 10,
            },
        },
    }

    bot = EvernoteBot('token', 'test_bot')
    message_id = random.randint(1, 100)
    bot.api.sendMessage = AsyncMock(return_value={'message_id': message_id})

    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)

    dealer = EvernoteDealer()
    handler = VoiceHandler()
    handler.downloader.telegram_api.getFile = AsyncMock(
        return_value='http://yandex.ru/robots.txt'
    )
    handler.evernote.create_note = AsyncMock()
    handler.evernote.update_note = AsyncMock()
    handler.telegram.editMessageText = AsyncMock()
    downloaded_filename = os.path.join(handler.downloader.download_dir,
                                       file_id)
    handler.get_files = AsyncMock(return_value=[(downloaded_filename, 'audio/wav')])
    dealer.handlers['voice'] = [handler]
    user_updates = dealer.fetch_updates()
    await dealer.process_user_updates(user, user_updates[user.id])
    await asyncio.sleep(0.1)

    assert handler.evernote.create_note.call_count == 1
    args = handler.evernote.create_note.call_args[0]
    assert args[0] == 'token'
    assert args[1] == 'Voice'
    assert args[2] == ''
    assert args[3] == user.current_notebook['guid']
    assert len(args[4]) == 1
    assert args[4][0][0] == downloaded_filename
    assert handler.get_files.call_count == 1
    assert handler.evernote.update_note.call_count == 0
    assert handler.telegram.editMessageText.call_count == 1
    args = handler.telegram.editMessageText.call_args[0]
    assert args[0] == user.telegram_chat_id
    assert args[1] == message_id
    assert 'Voice saved' in args[2]
