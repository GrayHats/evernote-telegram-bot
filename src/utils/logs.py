import logging
import smtplib
from os.path import join
from logging.handlers import SMTPHandler


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
    return {
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
            'file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, '%s.log' % project_name),
                'formatter': 'default',
            },
            'evernote_api_file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, 'evernote.log'),
                'formatter': 'default',
            },
            'telegram_api_file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, 'telegram.log'),
                'formatter': 'default',
            },
            'dealer_file': {
                'level': 'INFO',
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, 'dealer.log'),
                'formatter': 'default',
            },
            'downloader_file': {
                'level': 'DEBUG',
                'class': 'logging.FileHandler',
                'filename': join(logs_dir, 'downloader.log'),
                'formatter': 'default',
            },
            'email': {
                'level': 'ERROR',
                'class': 'src.utils.logs.SslSMTPHandler',
                'mailhost': (smtp_settings['host'], smtp_settings['port']),
                'fromaddr': smtp_settings['email'],
                'toaddrs': [smtp_settings['email']],
                'subject': '',
                'credentials': (smtp_settings['user'], smtp_settings['password']),
                'secure': (),
            },
        },

        'loggers': {
            'aiohttp.access': {
                'level': 'INFO',
                'handlers': ['accessfile'],
                'propagate': False,
            },
            'aiohttp.server': {
                'level': 'INFO',
                'handlers': ['file', 'email'],
                'propagate': False,
            },
            'gunicorn.access': {
                'level': 'INFO',
                'handlers': ['accessfile'],
                'propagate': False,
            },
            'gunicorn.error': {
                'level': 'INFO',
                'handlers': ['file', 'email'],
                'propagate': False,
            },
            # APIs
            'evernote_api': {
                'level': 'ERROR',
                'handlers': ['file', 'evernote_api_file', 'stdout', 'email'],
                'propagate': False,
            },
            'telegram_api': {
                'level': 'ERROR',
                'handlers': ['telegram_api_file', 'email'],
                'propagate': False,
            },
            # daemons
            'dealer': {
                'level': 'ERROR',
                'handlers': ['dealer_file', 'stdout', 'email'],
                'propagate': False,
            },
            'downloader': {
                'level': 'ERROR',
                'handlers': ['downloader_file', 'stdout', 'email'],
                'propagate': False,
            },
            # bot
            'bot': {
                'level': 'WARNING',
                'handlers': ['file', 'email'],
                'propagate': False,
            },
            '': {
                'level': 'ERROR',
                'handlers': ['file'],
                'propagate': True,
            },
        },
    }
