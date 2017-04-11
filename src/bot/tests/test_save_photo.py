import asyncio
import pytest
import datetime
import random
import os

from conftest import AsyncMock
from bot import EvernoteBot
from bot.dealer import EvernoteDealer
from bot.message_handlers import PhotoHandler


@pytest.mark.async_test
async def test_save_photo_multiple_notes_mode(user):
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
            'photo': [
                {
                    'file_size': 12345,
                    'file_id': file_id,
                    'mime_type': 'text/html',
                    'width': 800,
                    'height': 600,
                },
            ],
        },
    }

    bot = EvernoteBot('token', 'test_bot')
    message_id = random.randint(1, 100)
    bot.api.sendMessage = AsyncMock(return_value={'message_id': message_id})

    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)

    dealer = EvernoteDealer()
    handler = PhotoHandler()
    handler.downloader.telegram_api.getFile = AsyncMock(
        return_value='http://yandex.ru/robots.txt'
    )
    handler.evernote.create_note = AsyncMock()
    handler.evernote.update_note = AsyncMock()
    handler.telegram.editMessageText = AsyncMock()
    dealer.handlers['photo'] = [handler]
    user_updates = dealer.fetch_updates()
    await dealer.process_user_updates(user, user_updates[user.id])
    await asyncio.sleep(0.1)

    assert handler.evernote.create_note.call_count == 1
    args = handler.evernote.create_note.call_args[0]
    assert args[0] == 'token'
    assert args[1] == 'Photo'
    assert args[2] == ''
    assert args[3] == user.current_notebook['guid']
    assert len(args[4]) == 1
    assert args[4][0][0] == os.path.join(handler.downloader.download_dir,
                                         file_id)
    assert handler.evernote.update_note.call_count == 0
    assert handler.telegram.editMessageText.call_count == 1
    args = handler.telegram.editMessageText.call_args[0]
    assert args[0] == user.telegram_chat_id
    assert args[1] == message_id
    assert 'Photo saved' in args[2]


@pytest.mark.async_test
async def test_save_photo_one_note_mode(user):
    user.mode = 'one_note'
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
            'photo': [
                {
                    'file_size': 12345,
                    'file_id': file_id,
                    'mime_type': 'text/html',
                    'width': 800,
                    'height': 600,
                },
            ],
        },
    }

    bot = EvernoteBot('token', 'test_bot')
    message_id = random.randint(1, 100)
    bot.api.sendMessage = AsyncMock(return_value={'message_id': message_id})

    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)
    dealer = EvernoteDealer()
    handler = PhotoHandler()
    handler.downloader.telegram_api.getFile = AsyncMock(
        return_value='http://yandex.ru/robots.txt'
    )
    handler.evernote.create_note = AsyncMock()
    handler.evernote.update_note = AsyncMock()
    handler.telegram.editMessageText = AsyncMock()
    dealer.handlers['photo'] = [handler]
    user_updates = dealer.fetch_updates()
    await dealer.process_user_updates(user, user_updates[user.id])
    await asyncio.sleep(0.1)

    assert handler.evernote.create_note.call_count == 0
    assert handler.evernote.update_note.call_count == 1
    args = handler.evernote.update_note.call_args[0]
    notebook_guid = user.current_notebook['guid']
    note_guid = user.places[notebook_guid]
    assert args[0] == 'token'
    assert args[1] == note_guid
    assert args[2] == notebook_guid
    assert args[3] == ''
    files = args[4]
    assert len(files) == 1
    assert files[0][0] == os.path.join(handler.downloader.download_dir, file_id)
    assert not os.path.exists(files[0][0])
