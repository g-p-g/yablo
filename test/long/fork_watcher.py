import sys
import unittest

import redis

from yablo.service.btcd_ws import BitcoinWebsocket


class ReceiveBlockDisconnect(unittest.TestCase):

    def setUp(self):
        # Start a websocket client to receive notifications.
        rpcport1 = 20000
        red = redis.StrictRedis()
        fake_cfg = {'bitcoin_cfg': 'x', 'rpcuser': 'abc', 'rpcpass': 'def',
                    'rpcserver': '127.0.0.1', 'rpclisten': rpcport1}
        cli = BitcoinWebsocket(red, fake_cfg)
        cli.setup()
        print cli.getblockcount()
        self.cli_handler = cli.handle_message()

    def test_longwait_blockdisc(self):
        # Observe received notifications.
        print 'Waiting for blockdisconnected notification...'
        while True:
            print 'next!'
            res = next(self.cli_handler)
            print "ws client:", res
            if not res:
                # Likely a disconnect in websocket.
                continue
            if res['method'] == 'blockdisconnected':
                # Success.
                print "GOT IT"
                break


if __name__ == "__main__":
    unittest.main(verbosity=2)
