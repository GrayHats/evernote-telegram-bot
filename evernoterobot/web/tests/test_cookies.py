from web import cookies

def test_encode_decode():
    data = { 'k': 123, 's': 'hello' }
    encoded_cookies = cookies.encode(data)
    d = cookies.decode(encoded_cookies)
    assert d['k'] == 123
    assert d['s'] == 'hello'
    assert len(d.keys()) == 2