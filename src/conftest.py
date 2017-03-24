import sys
import gc
import contextlib
import os
from os.path import dirname
from os.path import realpath
import asyncio
from unittest.mock import Mock
import importlib
import shutil
import random
import string
import datetime

import pytest

from bot import EvernoteBot
from bot import User
from bot.model import Model
from ext.telegram.models import TelegramUpdate


sys.path.insert(0, realpath(dirname(dirname(__file__))))
config = importlib.import_module('config').config


def setup_test_loop():
    """create and return an asyncio.BaseEventLoop
    instance. The caller should also call teardown_test_loop,
    once they are done with the loop.
    """
    loop = asyncio.get_event_loop()
    # asyncio.set_event_loop(None)
    return loop


# def teardown_test_loop(loop):
#     """teardown and cleanup an event_loop created
#     by setup_test_loop.
#     :param loop: the loop to teardown
#     :type loop: asyncio.BaseEventLoop
#     """
#     is_closed = getattr(loop, 'is_closed')
#     if is_closed is not None:
#         closed = is_closed()
#     else:
#         closed = loop._closed
#     if not closed:
#         loop.call_soon(loop.stop)
#         loop.run_forever()
#         loop.close()
#     gc.collect()
    # asyncio.set_event_loop(None)


@contextlib.contextmanager
def loop_context():
    """a contextmanager that creates an event_loop, for test purposes.
    handles the creation and cleanup of a test loop.
    """
    loop = setup_test_loop()
    yield loop
    # teardown_test_loop(loop)


@pytest.yield_fixture
def loop():
    with loop_context() as loop:
        yield loop


def pytest_runtest_setup(item):
    if 'async_test' in item.keywords and 'loop' not in item.fixturenames:
        # inject an event loop fixture for all async tests
        item.fixturenames.append('loop')


@pytest.mark.tryfirst
def pytest_pyfunc_call(pyfuncitem):
    """
    Run asyncio marked test functions in an event loop instead of a normal
    function call.
    """
    if 'use_mongo' in pyfuncitem.keywords:
        config['storage'] = {
            'class': 'bot.storage.MongoStorage',
            'host': 'localhost',
            'port': 27017,
            'db': 'test',
        }
    if 'async_test' in pyfuncitem.keywords:
        funcargs = pyfuncitem.funcargs
        loop = funcargs['loop']
        testargs = {arg: funcargs[arg]
                    for arg in pyfuncitem._fixtureinfo.argnames}
        loop.run_until_complete(pyfuncitem.obj(**testargs))
        return True


@pytest.mark.tryfirst
def pytest_pycollect_makeitem(collector, name, obj):
    if collector.funcnamefilter(name):
        if not callable(obj):
            return
        item = pytest.Function(name, parent=collector)
        if 'async_test' in item.keywords:
            return list(collector._genfunctions(name, obj))


class AsyncMock(Mock):
    async def __call__(self, *args, **kwargs):
        return super().__call__(*args, **kwargs)


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


@pytest.fixture
def text_update(user):
    return TelegramUpdate({
        'update_id': 213,
        'message': {
            'message_id': 1,
            'date': datetime.datetime.now(),
            'from': {'id': user.id, 'username': 'test'},
            'chat': {'id': user.telegram_chat_id, 'type': 'private'},
            'text': 'test text'},
    })


@pytest.fixture
def testbot():
    bot = EvernoteBot(config['telegram']['token'], 'test_bot')
    bot.track = Mock()
    bot.api = AsyncMock()
    bot.api.sendMessage = AsyncMock(return_value={'message_id': 1})
    bot.evernote = AsyncMock()
    bot.evernote.get_oauth_data = AsyncMock(
        return_value={'oauth_url': 'test_oauth_url'}
    )
    bot.evernote.list_notebooks = AsyncMock(
        return_value=[{'guid': '1', 'name': 'test_notebook'}]
    )
    return bot


def delete_cached_files(root_dir):
    for dir_path, dirnames, filenames in os.walk(root_dir):
        for name in dirnames:
            path = os.path.join(dir_path, name)
            if name in ('__pycache__', '.cache'):
                shutil.rmtree(path)
        for name in filenames:
            filename = os.path.join(dir_path, name)
            _, ext = os.path.splitext(filename)
            if ext == '.pyc':
                os.unlink(filename)


delete_cached_files(realpath(dirname(__file__)))
