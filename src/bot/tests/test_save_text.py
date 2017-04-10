import asyncio
import pytest
import datetime
import random

from conftest import AsyncMock
from bot import EvernoteBot
from bot.dealer import EvernoteDealer
from bot.message_handlers import TextHandler


@pytest.mark.async_test
async def test_save_text_multiple_notes_mode(user):
    user.mode = 'multiple_notes'
    user.save()

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
            'text': 'test text',
        },
    }

    bot = EvernoteBot('token', 'test_bot')
    message_id = random.randint(1, 100)
    bot.api.sendMessage = AsyncMock(return_value={'message_id': message_id})

    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)

    dealer = EvernoteDealer()
    handler = TextHandler()
    handler.evernote.create_note = AsyncMock()
    handler.evernote.update_note = AsyncMock()
    handler.telegram.editMessageText = AsyncMock()
    dealer.handlers['text'] = [handler]

    user_updates = dealer.fetch_updates()
    await dealer.process_user_updates(user, user_updates[user.id])
    await asyncio.sleep(0.1)
    assert handler.evernote.create_note.call_count == 1
    args = handler.evernote.create_note.call_args[0]
    assert args[0] == 'token'
    assert args[1] == 'Text'
    assert args[2] == 'test text'
    assert args[3] == user.current_notebook['guid']
    assert handler.evernote.update_note.call_count == 0
    assert handler.telegram.editMessageText.call_count == 1
    args = handler.telegram.editMessageText.call_args[0]
    assert args[0] == user.telegram_chat_id
    assert args[1] == message_id
    assert 'Text saved' in args[2]
