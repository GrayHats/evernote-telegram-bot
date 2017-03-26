import logging
import logging.config
import smtplib
from os.path import join
from logging.handlers import SMTPHandler

from config import config


class SslSMTPHandler(SMTPHandler):
    def emit(self, record):
        """
        Emit a record.

        Format the record and send it to the specified addressees.
        """
        try:
            try:
                from email.utils import formatdate
            except ImportError:
                formatdate = self.date_time
            port = self.mailport
            if not port:
                port = smtplib.SMTP_PORT
            smtp = smtplib.SMTP_SSL(self.mailhost, port, timeout=1)
            msg = self.format(record)
            # subject = '[%s] %s' % (record.levelname, record.message)
            msg = "From: %s\r\nTo: %s\r\nSubject: %s\r\nDate: %s\r\n\r\n%s" % (
                            self.fromaddr,
                            ",".join(self.toaddrs),
                            self.getSubject(record),
                            formatdate(), msg)
            if self.username:
                # smtp.ehlo() # for tls add this line
                # smtp.starttls() # for tls add this line
                # smtp.ehlo() # for tls add this line
                smtp.login(self.username, self.password)
            smtp.sendmail(self.fromaddr, self.toaddrs, msg)
            smtp.quit()
        except (KeyboardInterrupt, SystemExit):
            raise
        except Exception as e:
            logger = logging.getLogger()
            logger.error(e, exc_info=1)
            # self.handleError(record)

    def getSubject(self, record):
        if record.message:
            return 'Evernoterobot [%s] %s' % (record.levelname, record.message)
        elif record.exc_info:
            return 'Evernoterobot [%s] %s' % (record.levelname, str(record.exc_info[1])[:30])
        return 'Evernoterobot [%s]' % record.levelname


def get_config(project_name, logs_dir, smtp_settings):

    def file_handler(filename, log_level='DEBUG'):
        return {
                'level': log_level,
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, filename),
                'formatter': 'default',
        }

    def logger(level='INFO', handlers=None, propagate=False):
        return {
            'level': level,
            'handlers': handlers or [],
            'propagate': propagate,
        }

    config = {
        'version': 1,
        'disable_existing_loggers': False,

        'formatters': {
            'default': {
                'format': '%(asctime)s - PID:%(process)d - %(levelname)s - %(message)s (%(pathname)s:%(lineno)d)',
            },
        },

        'handlers': {
            'stdout': {
                'class': 'logging.StreamHandler',
                'formatter': 'default',
            },
            'accessfile': {
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, 'access.log')
            },
            'file': file_handler('%s.log' % project_name),
            'evernote_api_file': file_handler('evernote.log'),
            'telegram_api_file': file_handler('telegram.log'),
            'dealer_file': file_handler('dealer.log', 'INFO'),
            'downloader_file': file_handler('downloader.log'),
            'email': file_handler('email.log', 'ERROR'),
        },

        'loggers': {
            'aiohttp.access': logger(handlers=['accessfile']),
            'aiohttp.server': logger(handlers=['file', 'email']),
            'gunicorn.access': logger(handlers=['accessfile']),
            'gunicorn.error': logger(handlers=['file', 'email']),
            # APIs
            'evernote_api': logger('ERROR', ['evernote_api_file', 'email']),
            'telegram_api': logger('ERROR', ['telegram_api_file', 'email']),
            # daemons
            'dealer': logger('ERROR', ['dealer_file', 'email']),
            'downloader': logger('ERROR', ['downloader_file', 'email']),
            # bot
            'bot': logger('WARNING', ['file', 'email']),
            '': logger('ERROR', ['file', 'email'], True),
        },
    }
    if smtp_settings:
        config['handlers']['email'] = {
                'level': 'ERROR',
                'class': 'utils.logs.SslSMTPHandler',
                'mailhost': (smtp_settings['host'], smtp_settings['port']),
                'fromaddr': smtp_settings['email'],
                'toaddrs': [smtp_settings['email']],
                'subject': '',
                'credentials': (
                    smtp_settings['user'],
                    smtp_settings['password']
                ),
                'secure': (),
        }
    return config


def get_logger(name=''):
    logging.config.dictConfig(get_config(
        project_name=config['project_name'],
        logs_dir=config['logs_dir'],
        smtp_settings=config.get('smtp')
    ))
    return logging.getLogger(name)
