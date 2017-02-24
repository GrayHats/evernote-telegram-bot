from bot import User
from ext.telegram.bot import TelegramBotCommand
from ext.telegram.models import Message


class SwitchModeCommand(TelegramBotCommand):

    name = 'switch_mode'

    async def execute(self, message: Message):
        self.bot.track(message)
        user = User.get({'id': message.user.id})
        buttons = []
        for mode in ['one_note', 'multiple_notes']:
            if user.mode == mode:
                name = "> %s <" % mode.capitalize().replace('_', ' ')
            else:
                name = mode.capitalize().replace('_', ' ')
            buttons.append({'text': name})
        self.bot.send_message(
            user.telegram_chat_id,
            'Please, select mode',
            {
                'keyboard': [[b] for b in buttons],
                'resize_keyboard': True,
                'one_time_keyboard': True,
            }
        )
        user.state = 'switch_mode'
        user.save()
