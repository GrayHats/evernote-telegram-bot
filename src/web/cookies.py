import settings
import json
import hmac
import base64


def encode(data: dict) -> str:
    key = settings.SECRET['secret_key']
    data = base64.b64encode(json.dumps(data).encode(), b'-_')
    signature = hmac.new(key.encode(), data).hexdigest()
    signature = base64.b64encode(signature.encode())
    return '{0}.{1}'.format(signature.decode(), data.decode())


def decode(data: str) -> dict:
    key = settings.SECRET['secret_key']
    signature, data = data.split('.')
    data = data.encode()
    signature = base64.b64decode(signature).decode()
    if signature == hmac.new(key.encode(), data).hexdigest():
        return json.loads(base64.b64decode(data, b'-_').decode())
