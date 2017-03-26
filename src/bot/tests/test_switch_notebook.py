import asyncio
import pytest
import datetime
import json
from collections import namedtuple
from bot import EvernoteBot
from bot.model import User
from conftest import AsyncMock


@pytest.mark.async_test
async def test_switch_notebook(user):
    update_data = {
        'update_id': 93710840,
        'message': {
            'date': datetime.datetime.now(),
            'from': {
                'username': user.username,
                'id': user.id,
            },
            'chat': {
                'id': user.id,
                'type': 'private',
                'username': user.username,
            },
            'message_id': 164,
            'text': '/notebook',
            'entities': [
                {
                    'type': 'bot_command',
                    'offset': 0,
                    'length': 9
                },
            ],
        },
    }

    bot = EvernoteBot('token', 'test_bot')
    Notebook = namedtuple('Notebook', ['guid', 'name'])
    notebooks = [
        Notebook(user.current_notebook['guid'], user.current_notebook['name']),
        Notebook(guid='123', name='test_nb')
    ]
    bot.evernote.api.list_notebooks = AsyncMock(return_value=notebooks)
    bot.evernote.create_note = AsyncMock()
    bot.evernote.get_note_link = AsyncMock()
    bot.api.editMessageText = AsyncMock()
    bot.api.sendMessage = AsyncMock()

    await bot.handle_update(update_data)

    user = User.get({'id': user.id})
    user.mode = 'multiple_notes'
    user.save()
    assert user.state == 'select_notebook'
    await asyncio.sleep(0.1)
    assert bot.api.sendMessage.call_args[0][1] == 'Please, select notebook'
    markup = json.loads(bot.api.sendMessage.call_args[0][2])
    assert markup['one_time_keyboard']
    assert markup['keyboard']
    nb = markup['keyboard'][0][0]
    assert nb['text'] == '> {0} <'.format(user.current_notebook['name'])

    bot.evernote.api.list_notebooks = AsyncMock(return_value=notebooks)
    bot.evernote.create_note.reset_mock()
    bot.api.sendMessage.reset_mock()

    update_data = {
        'update_id': 93710840,
        'message': {
            'date': datetime.datetime.now(),
            'from': {
                'username': user.username,
                'id': user.id,
            },
            'chat': {
                'id': user.id,
                'type': 'private',
                'username': user.username,
            },
            'message_id': 164,
            'text': 'test_nb',
        },
    }
    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)

    user = User.get({'id': user.id})
    assert user.current_notebook['guid'] == '123'
    assert bot.evernote.api.list_notebooks.call_count == 1
    assert bot.api.sendMessage.call_count == 1
    assert bot.api.sendMessage.call_args[0][1].startswith(
        'From now your current notebook is: test_nb'
    )
