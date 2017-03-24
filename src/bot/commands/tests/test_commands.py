import asyncio

import pytest

from bot import User
from bot import EvernoteBot
from bot.commands.help import HelpCommand
from bot.commands.notebook import NotebookCommand
from bot.commands.start import StartCommand
from bot.commands.switch_mode import SwitchModeCommand
from bot.model import StartSession


@pytest.mark.async_test
async def test_help_command(testbot: EvernoteBot, user, text_update):
    update = text_update
    help_cmd = HelpCommand(testbot)
    await help_cmd.execute(update.message)
    await asyncio.sleep(0.0001)
    assert testbot.api.sendMessage.call_count == 1
    args = testbot.api.sendMessage.call_args[0]
    assert len(args) == 4
    assert args[0] == user.telegram_chat_id
    assert 'This is bot for Evernote' in args[1]
    assert args[2] is None
    assert args[3] is None


@pytest.mark.async_test
async def test_notebook_command(testbot: EvernoteBot, user, text_update):
    update = text_update
    notebook_cmd = NotebookCommand(testbot)
    await notebook_cmd.execute(update.message)
    await asyncio.sleep(0.0001)
    user = User.get({'id': user.id})
    assert user.state == 'select_notebook'
    assert testbot.api.sendMessage.call_count == 1
    args = testbot.api.sendMessage.call_args[0]
    assert args[0] == user.telegram_chat_id
    assert args[1] == 'Please, select notebook'


@pytest.mark.async_test
async def test_start_command(testbot: EvernoteBot, text_update):
    update = text_update
    start_cmd = StartCommand(testbot)
    await start_cmd.execute(update.message)
    await asyncio.sleep(0.0001)
    sessions = StartSession.find()
    assert len(sessions) == 1
    assert sessions[0].id == update.message.user.id
    assert sessions[0].oauth_data['oauth_url'] == 'test_oauth_url'
    assert testbot.api.sendMessage.call_count == 1
    args = testbot.api.sendMessage.call_args[0]
    assert len(args) == 4
    assert 'Welcome' in args[1]
    assert testbot.api.editMessageReplyMarkup.call_count == 1


@pytest.mark.async_test
async def test_switch_mode_command(testbot: EvernoteBot, text_update):
    update = text_update
    switch_mode_cmd = SwitchModeCommand(testbot)
    user = User.create(id=update.message.user.id,
                       telegram_chat_id=update.message.chat.id,
                       mode='one_note')
    await switch_mode_cmd.execute(update.message)
    await asyncio.sleep(0.0001)
    user = User.get({'id': user.id})
    assert user.state == 'switch_mode'
    assert testbot.api.sendMessage.call_count == 1
    args = testbot.api.sendMessage.call_args[0]
    assert len(args) == 4
    assert args[0] == user.telegram_chat_id
    assert 'Please, select mode' == args[1]
