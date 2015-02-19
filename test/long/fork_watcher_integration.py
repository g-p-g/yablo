import sys
import time
import atexit

import redis
import requests

from yablo.service.btcd_ws import BitcoinWebsocket
from yablo.api import watch_discblock, cancel_watch


# Subscribe for discblock events.
port = int(sys.argv[1])
route = sys.argv[2]
baseurl = 'http://localhost:%d/' % port
url = baseurl + route
res = watch_discblock(url)
evt_id = res['id']

# When leaving, remove this subscriber.
atexit.register(lambda: cancel_watch(evt_id))


# Start a websocket client to receive notifications.
rpcport1 = 20000
red = redis.StrictRedis()
fake_cfg = {'bitcoin_cfg': 'x', 'rpcuser': 'abc', 'rpcpass': 'def',
            'rpcserver': '127.0.0.1', 'rpclisten': rpcport1}
cli = BitcoinWebsocket(red, fake_cfg)
cli.setup()
cli_handler = cli.handle_message()
print cli.getblockcount()


# Observe received notifications.
print 'Waiting for blockdisconnected notification...'
while True:
    print 'next!'
    res = next(cli_handler)
    print "ws client:", res
    if not res:
        # Likely a disconnect in websocket.
        continue
    if res['method'] == 'blockdisconnected':
        # Success.
        print "GOT IT"
        break


# At this point we have observed a blockdisconnected event from btcd.
# It's a matter of yablo processing it and dispatching to the
# subscriber created earlier.
for i in xrange(1, 11):
    res = int(requests.get(baseurl + 'count').text)
    if res:
        print 'checks before receiving callback: %d' % i
        break
    time.sleep(0.1)
else:
    raise 'http server did not receive callback'
