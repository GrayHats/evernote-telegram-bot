import asyncio
import pytest
import datetime

from config import config
from bot import EvernoteBot
from conftest import AsyncMock
from bot.model import User
from bot.model import StartSession


@pytest.mark.async_test
async def test_requre_full_permissions(user):
    StartSession.create(
        id=user.id,
        key='',
        data={},
        oauth_data={}
    )
    config['evernote']['full_access'] = {}

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
            'text': '/switch_mode',
            'entities': [
                {
                    'type': 'bot_command',
                    'offset': 0,
                    'length': 12
                },
            ],
        },
    }

    bot = EvernoteBot('token', 'test_bot')
    bot.api.sendMessage = AsyncMock()

    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)
    user = User.get({'id': user.id})
    user.mode = 'multiple_notes'
    user.save()
    assert user.state == 'switch_mode'
    assert bot.api.sendMessage.call_count == 1
    args = bot.api.sendMessage.call_args[0]
    assert args[1] == 'Please, select mode'

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
            'text': 'One note',
        },
    }

    bot.api.sendMessage = AsyncMock(return_value={'message_id': 123})
    bot.api.editMessageReplyMarkup = AsyncMock()
    bot.evernote.get_oauth_data = AsyncMock(return_value={'oauth_url': 'url'})
    await bot.handle_update(update_data)
    await asyncio.sleep(0.1)

    session = StartSession.get({'id': user.id})
    assert session.oauth_data['oauth_url'] == 'url'
    assert bot.evernote.get_oauth_data.call_count == 1
    assert bot.api.editMessageReplyMarkup.call_count == 1
    assert bot.api.sendMessage.call_count == 2
    # TODO: check call args
