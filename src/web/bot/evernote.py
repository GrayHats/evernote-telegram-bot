import functools
from urllib.parse import parse_qs

import asyncio
from aiohttp import web
from requests_oauthlib.oauth1_session import TokenRequestDenied

from config import config
from bot.model import User, StartSession, ModelNotFound


async def oauth_callback(request):
    logger = request.app.logger
    bot = request.app.bot
    config_data = config['evernote']['basic_access']
    params = parse_qs(request.query_string)
    callback_key = params.get('key', [''])[0]
    session_key = params.get('session_key')[0]
    try:
        session = StartSession.get({'oauth_data.callback_key': callback_key})
    except ModelNotFound as e:
        logger.error(e, exc_info=1)
        return web.HTTPForbidden()

    if not params.get('oauth_verifier'):
        logger.info('User declined access. No access token =(')
        bot.send_message(session.data['chat_id'],
                         'We are sorry, but you declined authorization 😢')
        return web.HTTPFound(bot.url)
    if session.key != session_key:
        text = 'Session is expired. \
Please, send /start command to create new session'
        bot.send_message(session.data['chat_id'], text)
        return web.HTTPFound(bot.url)

    user_data = session.data['user']
    name = '{0} {1}'.format(user_data['first_name'], user_data['last_name'])
    user = User(id=session.id,
                name=name,
                username=user_data['username'],
                telegram_chat_id=session.data['chat_id'],
                mode='multiple_notes',
                places={},
                settings={'evernote_access': 'basic'})
    try:
        future = asyncio.ensure_future(
            bot.evernote.get_access_token(
                config_data['key'],
                config_data['secret'],
                session.oauth_data['oauth_token'],
                session.oauth_data['oauth_token_secret'],
                params['oauth_verifier'][0]
            )
        )
        future.add_done_callback(
            functools.partial(set_access_token, bot, user)
        )
    except TokenRequestDenied as e:
        logger.error(e, exc_info=1)
        text = 'We are sorry, but we have some problems with Evernote \
connection. Please try again later'
        bot.send_message(user.telegram_chat_id, text)
    except Exception as e:
        logger.fatal(e, exc_info=1)
        bot.send_message(user.telegram_chat_id, 'Oops. Unknown error')

    text = 'Evernote account is connected.\n\
From now you can just send message and note be created.'
    bot.send_message(user.telegram_chat_id, text)
    user.save()
    return web.HTTPFound(bot.url)


def set_access_token(bot, user, future_access_token):
    access_token = future_access_token.result()
    user.evernote_access_token = access_token
    user.save()
    future = asyncio.ensure_future(
        bot.evernote.get_default_notebook(access_token)
    )
    future.add_done_callback(functools.partial(on_notebook_info, bot, user))


def on_notebook_info(bot, user, future_notebook):
    notebook = future_notebook.result()
    user.current_notebook = {
        'guid': notebook.guid,
        'name': notebook.name,
    }
    text = 'Current notebook: %s\nCurrent mode: %s' % (
        notebook.name, user.mode.replace('_', ' ').capitalize()
    )
    bot.send_message(user.telegram_chat_id, text)
    user.save()


async def oauth_callback_full_access(request):
    logger = request.app.logger
    bot = request.app.bot
    params = parse_qs(request.query_string)
    callback_key = params.get('key', [''])[0]
    session_key = params.get('session_key')[0]
    try:
        session = StartSession.get({'oauth_data.callback_key': callback_key})
        user = User.get({'id': session.id})
    except ModelNotFound as e:
        logger.error(e, exc_info=1)
        return web.HTTPForbidden()

    if not params.get('oauth_verifier'):
        logger.info('User declined full access =(')
        bot.send_message(
            user.telegram_chat_id,
            'We are sorry, but you deny read/update access😢',
            {'hide_keyboard': True}
        )
        return web.HTTPFound(bot.url)
    if session.key != session_key:
        text = 'Session is expired. Please, send /start command to create \
new session'
        bot.send_message(user.telegram_chat_id, text)
        return web.HTTPFound(bot.url)
    try:
        oauth_verifier = params['oauth_verifier'][0]
        config_data = config['evernote']['full_access']
        future = asyncio.ensure_future(
            bot.evernote.get_access_token(config_data, session.oauth_data,
                                          oauth_verifier)
        )
        future.add_done_callback(
            functools.partial(switch_to_one_note_mode, bot, user.id)
        )
    except TokenRequestDenied as e:
        logger.error(e, exc_info=1)
        bot.send_message(
            user.telegram_chat_id,
            'We are sorry, but we have some problems with Evernote connection.\
 Please try again later',
            {'hide_keyboard': True}
        )
    except Exception as e:
        logger.fatal(e, exc_info=1)
        bot.send_message(user.telegram_chat_id, 'Oops. Unknown error',
                         {'hide_keyboard': True})
    text = 'From now this bot in "One note" mode'
    bot.send_message(user.telegram_chat_id, text,
                     {'hide_keyboard': True})
    return web.HTTPFound(bot.url)


def switch_to_one_note_mode(bot, user_id, access_token_future):
    user = User.get({'id': user_id})
    access_token = access_token_future.result()
    user.evernote_access_token = access_token
    user.settings['evernote_access'] = 'full'
    user.mode = 'one_note'
    user.save()
    future = asyncio.ensure_future(
        bot.evernote.create_note(
            user.evernote_access_token,
            'Note for Evernoterobot',
            '',
            user.current_notebook['guid']
        )
    )
    future.add_done_callback(
        functools.partial(save_default_note_guid, user_id)
    )


def save_default_note_guid(user_id, note_guid_future):
    user = User.get({'id': user_id})
    note_guid = note_guid_future.result()
    user.places[user.current_notebook['guid']] = note_guid
    user.save()
