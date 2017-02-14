import socket

if socket.gethostname() in ['hamster']:
    from .base import *
else:
    from .dev import *
