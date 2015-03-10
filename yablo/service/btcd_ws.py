"""
Communicate with btcd (the bitcoin implementation in Go from Conformal)
through websocket and use Redis to publish events ready to be processed.
"""
import ssl
import json
import time
import random
import socket
import logging

import websocket

from .. import config, error
from ..storage import redis_keys


KNOWN_NOTIFICATIONS = frozenset([
    'blockconnected',
    'blockdisconnected',
    'txacceptedverbose'
])


class BitcoinRPC(object):
    """
    This is expected to be used as a mix-in.
    It expects that an object named wss exists.

    The number of bytes sent through wss are stored in the current
    instance under nsent.
    """

    def getblockcount(self):
        self.nsent = self.wss.send(method='getblockcount')
        return self._recv()

    def getblockhash(self, height):
        self.nsent = self.wss.send(method='getblockhash', params=[height])
        return self._recv()

    def getblock(self, block_hash, verbose=True, verbose_tx=True):
        params = [block_hash, verbose, verbose_tx]
        self.nsent = self.wss.send(method='getblock', params=params)
        return self._recv()

    def getrawtransaction(self, txid, verbose=True):
        params = [txid, int(verbose)]
        self.nsent = self.wss.send(method='getrawtransaction', params=params)
        return self._recv()

    def _recv(self):
        response = self.wss.recv()
        if response:
            return response['result']


class BitcoinWebsocket(BitcoinRPC):

    def __init__(self, red, cfg=None):
        """
        :param red: a redis.StrictRedis instance
        """
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())

        self.red = red
        self.cfg = cfg or config.app_config
        if not self.cfg.get('bitcoin_cfg'):
            raise error.ConfigException('bitcoin config file is missing')

        self.wss = None
        self.wss_notifier = None

    def setup(self, retry=10, notifier=True):
        """
        Open one or two connections to the btcd websocket server.

        :param int retry: number of connection attempts to perform
        :param bool notifier: if True, another connection will be
            set up for receiving notifications
        """
        self.use_notifier = notifier
        self.wss = WebsocketConnection(self.cfg, self.logger, retry)
        if notifier:
            # Open another connection that will be used only to listen
            # for notifications.
            self.wss_notifier = WebsocketConnection(self.cfg, self.logger,
                                                    retry, notifier=True)

    def handle_message(self):
        """
        One infinite generator loop.
        """
        if self.wss_notifier is None or self.wss is None:
            raise error.YabloException("notifier is not available")

        while True:
            result = self._process_one(self.wss_notifier)
            if result is None:
                self.logger.debug('reconnecting regular wss')
                self.wss = WebsocketConnection(self.cfg, self.logger)
            yield result

    def _process_one(self, conn):
        """
        Process one message and return.
        """
        msg = conn.recv()
        if msg is None:
            # Caused by a disconnect.
            return

        method = None
        if 'method' in msg:
            # Websocket notification.
            method = msg['method']
        elif msg['id']:
            # Result of a regular call through websockets.
            method = msg['id'].split('_')[0]

        if method not in KNOWN_NOTIFICATIONS:
            return _error_msg('unknown method, discarded', msg)

        if method == 'txacceptedverbose':
            self.logger.debug("new transaction %s", msg['params'][0]['txid'])
            self._handle_txaccepted(msg['params'])
        elif method == 'blockconnected':
            self.logger.debug("new block %r", msg['params'])
            self._handle_blockconnected(msg['params'])
        elif method == 'blockdisconnected':
            self.logger.warning("block disconnected %r", msg)
            self._handle_blockdisconnected(msg['params'])

        return msg

    def _handle_txaccepted(self, tx):
        """Received notification about a new transaction."""
        for trans in tx:
            # Leave only the essential keys/values required for the notification.
            push_stripped_trans(self.red, self.wss, trans)

    def _handle_blockconnected(self, data):
        """Received notification about a new block. Get more details."""
        block_hash, height = data

        # Send a getblock request outside the notifier connection
        # to avoid mixing messages.
        while True:
            nsent = self.wss.send(method='getblock',
                                  params=[block_hash, True, False])
            if nsent is None:
                self.logger.debug("wss.send for getblock failed, retrying")
                continue
            block = self.wss.recv()
            if block:
                block = block['result']
                break
            else:
                self.logger.debug("wss.recv failed, retrying")

        if block is None:
            # The value for 'result' is None, this has been observed when
            # a fork happens. Do nothing.
            self.logger.warning('empty result for getblock %s (height %d)',
                                block_hash, height)
            return

        assert block['height'] == height
        push_stripped_block(self.red, block)

    def _handle_blockdisconnected(self, data):
        """A given block has been removed from the main chain."""
        block_hash, height = data
        push_stripped_discblock(self.red, block_hash, height)


class WebsocketConnection(object):

    def __init__(self, cfg, logger, retry=10, notifier=False):
        """
        Manager a connection to the btcd websocket server.

        :param int retry: number of connection attempts to perform using
            exponential backoff.
        :bool notifier: if True, configure notifications to be received
        """
        self.cfg = cfg
        self.logger = logger

        self.retry = retry
        self.notifier = notifier

        self.wss = None
        self._setup()

    def send(self, retry=True, **kwargs):
        while True:
            try:
                result = _send_from(self.wss, kwargs)
            except socket.error, err:
                self.logger.exception(err)
                self.wss = None
                # Reconnect.
                self._setup()
                if not retry:
                    break
                self.logger.debug('retrying %r', kwargs)
            else:
                return result

    def recv(self, retry=False):
        while True:
            try:
                result = json.loads(self.wss.recv())
            except websocket._exceptions.WebSocketConnectionClosedException:
                self.logger.info("Disconnected")
                self.wss = None
                # Reconnect.
                self._setup()
                if not retry:
                    break
                self.logger.debug('retrying recv')
            else:
                return result

    def _setup(self):
        wss = self._connect()
        if wss is None:
            raise error.YabloException("Could not connect to the server")

        # Authenticate to the websocket server.
        data = {
            'method': 'authenticate',
            'id': 'auth',
            'params': [self.cfg['rpcuser'], self.cfg['rpcpass']],
        }
        _send_from(wss, data)
        res = json.loads(wss.recv())
        _fail_ifdiff(res['id'], data['id'])

        self.wss = wss
        if self.notifier:
            _setup_notifier(self.wss)

    def _connect(self):
        if 'bitcoin_cert' in self.cfg:
            cert = self.cfg['bitcoin_cert']
            opts = {
                'ca_certs': cert,
                'cert_reqs': ssl.CERT_REQUIRED,
            }
            protocol = 'wss'
        else:
            opts = {}
            protocol = 'ws'

        attempt = 0
        nretries = self.retry
        retry = nretries if nretries > 0 else 1
        while attempt < retry:
            try:
                wss = websocket.create_connection(
                    protocol + '://%(rpcserver)s:%(rpclisten)s/ws' % self.cfg,
                    sslopt=opts)
                return wss
            except socket.error, err:
                sleep = (2 ** attempt) + random.random()
                self.logger.debug('%s. Retrying in %s seconds', err, sleep)
                time.sleep(sleep)

            attempt += 1


def push_stripped_trans(red, wss, trans, dry_run=False):
    t_output = _collect_vout(trans)
    t_input = _collect_vin(trans, wss)

    stripped_tx = {
        't': trans['txid'],
        'o': t_output,
        'i': t_input,
        'c': trans.get('confirmations', 0),
        'b': trans.get('blockhash', None)
    }
    evt = {'type': redis_keys.EVENT_NEW_TRANS, 'data': stripped_tx}
    if not dry_run:
        red.rpush(redis_keys.HANDLE_EVENT, json.dumps(evt))
    return evt


def push_stripped_block(red, block, dry_run=False):
    stripped_block = {
        'b': block['hash'],
        'h': block['height'],
        'p': block['previousblockhash'],
        'd': block['difficulty'],
        'ts': block['time'],
        'tx': block['tx']
    }
    evt = {'type': redis_keys.EVENT_NEW_BLOCK, 'data': stripped_block}
    if not dry_run:
        red.rpush(redis_keys.HANDLE_EVENT, json.dumps(evt))
    return evt


def push_stripped_discblock(red, block_hash, block_height, dry_run=False):
    val = {
        'b': block_hash,
        'h': block_height
    }
    evt = {'type': redis_keys.EVENT_BLOCKDISC, 'data': val}
    if not dry_run:
        red.rpush(redis_keys.HANDLE_EVENT, json.dumps(evt))
    return evt


def _collect_vout(trans):
    t_output = []

    for vout in trans['vout']:
        if vout['scriptPubKey']['type'] in ('nonstandard', 'nulldata'):
            continue
        addresses = vout['scriptPubKey']['addresses']
        value = int(vout['value'] * 1e8)
        t_output.append({'a': addresses, 'v': value})

    return t_output


def _collect_vin(trans, wss):
    t_input = []

    for vin in trans['vin']:
        if 'coinbase' in vin:
            continue

        # Grab the input transaction.
        while True:
            nsent = wss.send(method='getrawtransaction', params=[vin['txid'], 1])
            if nsent is None:
                # getrawtransaction failed, retry.
                continue
            msg = wss.recv()
            if msg is not None:
                break
            # recv failed, retry.

        n = vin['vout']
        txref_vout = msg['result']['vout'][n]
        addresses = txref_vout['scriptPubKey']['addresses']
        value = int(txref_vout['value'] * 1e8)
        t_input.append({'a': addresses, 'v': value})

    return t_input


def _fail_ifdiff(got, expected):
    if got != expected:
        raise error.YabloException("Unexpected id %r (should be %r)" % (
            got, expected))


def _limit(t, max_size=512):
    res = repr(t)
    if len(res) > max_size - 2:
        res = '%s..' % res[:max_size - 2]
    return res


def _send_from(conn, params):
    _format_send(params)
    return conn.send(json.dumps(params))


def _setup_notifier(conn):
    # Listen for new transactions.
    data = {
        'method': 'notifynewtransactions',
        'id': 'ntt',
        # Be verbose
        'params': [True]
    }
    _send_from(conn, data)
    _fail_ifdiff(json.loads(conn.recv())['id'], data['id'])

    # Listen for notifications about blocks.
    data = {
        'method': 'notifyblocks',
        'id': 'nb'
    }
    _send_from(conn, data)
    _fail_ifdiff(json.loads(conn.recv())['id'], data['id'])


def _format_send(d):
    if 'method' not in d:
        raise error.YabloException('Message is missing the "method" key: %s',
                                   _limit(d))
    if 'id' not in d:
        d['id'] = d['method'] + '_'


def _error_msg(reason, msg):
    return {"error": reason, "original": msg}
