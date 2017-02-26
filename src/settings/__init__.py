import socket

if socket.gethostname() in ['hamster']:
    from .live import *
else:
    from .dev import *
