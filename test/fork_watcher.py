import sys

import redis

from yablo.service.btcd_ws import BitcoinWebsocket


# Start a websocket client to receive notifications.
rpcport1 = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
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
