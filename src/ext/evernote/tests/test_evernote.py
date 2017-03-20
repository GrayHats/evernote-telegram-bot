import pytest
import string
import random
import os
from config import config
from ext.evernote.client import Evernote


@pytest.fixture
def evernote_config():
    return config['evernote']['tests']


@pytest.mark.skip(reason='Enable for evernote api debugging')
@pytest.mark.async_test
async def test_create_note(evernote_config):
    token = evernote_config['access_token']
    evernote = Evernote(title_prefix='[TESTS]')
    random_name = ''.join([random.choice(string.ascii_letters)
                           for i in range(10)])
    test_filename = '/tmp/{name}.txt'.format(name=random_name)
    with open(test_filename, 'w') as f:
        f.write('test')
    note_guid = await evernote.create_note(
        token,
        '[Test note]',
        '',
        evernote_config['notebook_guid'],
        files=[(test_filename, 'text/plain')]
    )
    os.unlink(test_filename)
    note = await evernote.get_note(token, note_guid)
    assert note


@pytest.mark.skip(reason='Enable for evernote api debugging')
@pytest.mark.async_test
async def test_update_note(evernote_config):
    token = evernote_config['access_token']
    nb_guid = evernote_config['notebook_guid']
    evernote = Evernote(title_prefix='[TESTS]')
    # try update note that not exists. Note must be created
    random_guid = 'a256a12f-b6d2-365a-b259-adb9d7acfc32'
    await evernote.update_note(token, random_guid, nb_guid, 'created')

    note_guid = await evernote.create_note(token, '[Test note]', '', nb_guid)
    await evernote.update_note(token, note_guid, nb_guid, '111')
    random_name = ''.join([random.choice(string.ascii_letters)
                           for i in range(10)])
    test_filename = '/tmp/{name}.txt'.format(name=random_name)
    with open(test_filename, 'w') as f:
        f.write('test')
    await evernote.update_note(token, note_guid, nb_guid, '222',
                               files=[(test_filename, 'text/plain')])
    os.unlink(test_filename)
    note = await evernote.get_note(token, note_guid)
    assert note
