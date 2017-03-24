import asyncio
import string
import datetime
import random

import pytest

from bot.dealer import EvernoteDealer
from bot.model import TelegramUpdate
from bot.model import User
from bot.message_handlers import TextHandler
from conftest import AsyncMock


def generate_string(length):
    symbols = [random.choice(string.ascii_letters) for x in range(1, length)]
    return ''.join(symbols)


@pytest.fixture
def user():
    note_guid = generate_string(32)
    notebook_guid = generate_string(32)
    user = User.create(
        id=random.randint(1, 100),
        name=generate_string(5),
        username=generate_string(5),
        telegram_chat_id=random.randint(1, 100),
        mode='one_note',
        evernote_access_token='token',
        current_notebook={'guid': notebook_guid, 'name': 'test_notebook'},
        places={notebook_guid: note_guid}
    )
    return user


def test_fetch_updates():
    TelegramUpdate.create(user_id=1,
                          request_type='text',
                          status_message_id=2,
                          message={'data': 'ok'},
                          created=datetime.datetime(2016, 9, 1, 12, 30, 4))
    TelegramUpdate.create(user_id=1,
                          request_type='text',
                          status_message_id=3,
                          message={'data': 'woohoo'},
                          created=datetime.datetime(2016, 9, 1, 12, 30, 1))
    TelegramUpdate.create(user_id=2,
                          request_type='text',
                          status_message_id=4,
                          message={'data': 'yeah!'},
                          created=datetime.datetime(2016, 9, 1, 12, 30, 2))
    dealer = EvernoteDealer()
    user_updates = dealer.fetch_updates()
    updates = user_updates[1]
    updates2 = user_updates[2]
    assert len(updates) == 2
    assert len(updates2) == 1
    assert updates[0].created < updates2[0].created < updates[1].created
    assert updates[0].status_message_id == 3
    assert updates[1].status_message_id == 2
    assert updates2[0].status_message_id == 4


@pytest.mark.async_test
async def test_process_user_updates(user):
    update = TelegramUpdate.create(
        user_id=user.id,
        request_type='text',
        status_message_id=2,
        message={
            'message_id': 1,
            'date': datetime.datetime.now(),
            'from': {'id': user.id, 'username': 'test'},
            'chat': {'id': 123, 'type': 'private'},
            'text': 'test text'},
        created=datetime.datetime(2016, 9, 1, 12, 30, 4)
    )
    dealer = EvernoteDealer()
    handler = TextHandler()
    handler.evernote.create_note = AsyncMock()
    handler.evernote.update_note = AsyncMock()
    handler.telegram.editMessageText = AsyncMock()
    dealer.handlers['text'] = [handler]
    await dealer.process_user_updates(user, [update])
    await asyncio.sleep(0.1)
    assert handler.evernote.update_note.call_count == 1
    assert handler.telegram.editMessageText.call_count == 1
