import pytest
import string
import random
import os
from config import config
from ext.evernote.client import Evernote


@pytest.fixture
def evernote_config():
    return config['evernote']['tests']


@pytest.mark.async_test
async def test_create_note(evernote_config):
    evernote = Evernote()
    random_name = ''.join([random.choice(string.ascii_letters) for i in range(10)])
    test_filename = '/tmp/{name}.txt'.format(name=random_name)
    with open(test_filename, 'w') as f:
        f.write('test')
    await evernote.create_note(
        evernote_config['access_token'],
        '[Test note]',
        '',
        evernote_config['notebook_guid'],
        files=[(test_filename, 'text/plain')],
        title_prefix='[DEV BOT]'
    )
    os.unlink(test_filename)


@pytest.mark.async_test
async def test_update_note(evernote_config):
    evernote = Evernote()
    note_guid = await evernote.create_note(
        evernote_config['access_token'],
        '[Test note]',
        '',
        evernote_config['notebook_guid'],
        files=[],
        title_prefix='[DEV BOT]'
    )
    await evernote.update_note(
        evernote_config['access_token'],
        note_guid,
        evernote_config['notebook_guid'],
        '111',
        files=[]
    )
    random_name = ''.join([random.choice(string.ascii_letters) for i in range(10)])
    test_filename = '/tmp/{name}.txt'.format(name=random_name)
    with open(test_filename, 'w') as f:
        f.write('test')
    await evernote.update_note(
        evernote_config['access_token'],
        note_guid,
        evernote_config['notebook_guid'],
        '222',
        files=[(test_filename, 'text/plain')]
    )
    os.unlink(test_filename)
