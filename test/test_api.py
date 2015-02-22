# -*- encoding: utf-8 -*-
import unittest

from yablo import api


class TestQuery(unittest.TestCase):

    def test_query_notspecified(self):
        for notspecified in (None, ''):
            res = api.query(notspecified)
            self.assertEqual(res.get('code'), 400)
            self.assertIn('msg', res)
            self.assertEqual(res['msg'], 'query not specified')

    def test_query_unknown(self):
        for unknown in ('foo', '?', u'çáé', '-1', '1e30', -1, 1e100, '1.35'):
            res = api.query(unknown)
            self.assertIn('query', res)
            self.assertIn('data', res)
            self.assertEqual(res['query'], res['data'])
            self.assertEqual(res['query'], None)

    def test_query_empty(self):
        h = 'f' * 64
        res = api.query(h)
        self.assertIn('data', res)
        self.assertIn('query', res)
        self.assertEqual(res['data'], None)
        self.assertIn('txid', res['query'])
        self.assertIn('block_hash', res['query'])

    def test_query_block(self):
        # Query by height.
        res = api.query(0)
        self.assertIn('query', res)
        self.assertIn('height', res['query'])
        self.assertEqual(1, len(res['query']))
        self.assertIn('data', res)
        self.assertEqual(res['data']['height'], 0)

        # Query the same block but by its hash.
        blockhash = res['data']['hash']
        block = api.query(blockhash)
        self.assertEqual(block['data'], res['data'])
        self.assertIn('query', block)
        self.assertIn('block_hash', block['query'])
        self.assertEqual(1, len(block['query']))

    def test_query_bestblock(self):
        rescmp = api.query('bestblock')
        self.assertIn('query', rescmp)
        self.assertIn('custom', rescmp['query'])
        self.assertIn('lastblock', rescmp['query'])
        self.assertEqual(2, len(rescmp['query']))

        # Test for variations that produce the same result.
        for q in ('lastblock', 'best block', 'last block', 'LAST BLOCK',
                  'the last block'):
            # This will fail if a new block is received while this
            # loop is running.
            block = api.query(q)
            self.assertEqual(block, rescmp, 'failed for "%s"' % q)

    def test_query_tx(self):
        tx = _get_txid(blockheight=0)
        if tx is None:
            self.fail('no txid found in block 0')

        res = api.query(tx)
        self.assertEqual(res.get('query'), ['txid'])
        self.assertIn('data', res)
        self.assertEqual(tx, res['data']['txid'])

        res = api.query(tx[:-1] + 'x')
        self.assertEqual(res.get('query'), ['txid', 'block_hash'])
        self.assertEqual(res.get('data', ''), None)

    def test_query_address(self):
        addr = _get_address(blockheight=0)
        if addr is None:
            self.fail('no address found in block 0')

        res = api.query(addr)
        self.assertIn('query', res)
        self.assertIn('address', res['query'])
        self.assertEqual(1, len(res['query']))
        self.assertIn('data', res)
        self.assertEqual(res['data'].get('address'), addr)
        self.assertEqual(res['data'].get('note'), 'not implemented')

        invalid_addr = addr[:-1] + 'x'
        res = api.query(invalid_addr)
        self.assertEqual(res.get('query'), ['address'])
        self.assertEqual(res.get('data', ''), None)


class TestWatch(unittest.TestCase):

    def setUp(self):
        self.evt_list = set()

    def tearDown(self):
        for evt in self.evt_list:
            print 'removing %s' % evt
            api.cancel_watch(evt)

    def test_watchaddress(self):
        cb = 'http://localhost:10000/abc'

        for invalid in ('a', '?', '', None):
            res = api.watch_address(invalid, cb)
            self.assertEqual(res.get('msg'), 'invalid address')

        for test in ('1' * 30, ):  # Addresses are not validated here.
            res = api.watch_address(test, cb)
            self._check_watchaddress(res, cb, test)

    def test_watchnewblocks(self, etype='newblock', func=api.watch_newblocks):
        for invalid in (None, ''):
            res = func(invalid)
            if 'id' in res:
                # This shouldn't happen.
                self.evt_list.add(res['id'])
                self.fail('succeeded with callback = "%s"' % invalid)

            self.assertIn('msg', res)
            self.assertEqual(res.get('code'), 400)
            self.assertTrue(res['msg'].startswith('invalid callback '))

        cb = 'http://localhost:10000/abc'
        res = func(cb)
        self._check_watchblock(res, cb, etype)

    def test_watchdiscblocks(self):
        self.test_watchnewblocks('discblock', func=api.watch_discblock)

    def test_watchnewblocks_roundtrip(self):
        # Active -> Active -> Cancel -> Activate again using the same callback.
        cb = 'http://localhost:20004/abcdef'

        # First Active.
        res = api.watch_newblocks(cb)
        self._check_watchblock(res, cb, 'newblock')

        # Try activating again.
        res2 = api.watch_newblocks(cb)
        self.assertEqual(res2.get('msg'), 'already exists')
        self.assertEqual(res2.get('code'), 409)
        self.assertEqual(res2.get('success', ''), False)

        # Cancel it.
        res = api.cancel_watch(res['id'])
        self.assertEqual(res, {'success': True})

        # Activate again.
        res = api.watch_newblocks(cb)
        self._check_watchblock(res, cb, 'newblock')

    def test_twosubs_oneaddress(self):
        cb1 = 'http://localhost:12345/abc'
        cb2 = 'http://localhost:12345/def'
        addy = '12' * 15

        evt1 = api.watch_address(addy, cb1)
        self._check_watchaddress(evt1, cb1, addy)
        evt2 = api.watch_address(addy, cb2)
        self._check_watchaddress(evt2, cb2, addy)

        self.assertEqual(evt1['address'], evt2['address'])
        self.assertNotEqual(evt1['id'], evt2['id'])

    def test_onesub_twoaddresses(self):
        cb1 = 'http://localhost:12345/xyz'
        addy1 = '13' * 15
        addy2 = '14' * 15

        evt1 = api.watch_address(addy1, cb1)
        self._check_watchaddress(evt1, cb1, addy1)
        # Currently there is a limitation in how subscribers are stored
        # which causes all watch addresses for a given subscriber to
        # be active or inactive.
        #
        # So if you subscribe to two different addresses, then cancel
        # the subscription, and then subscribe to the same two addresses
        # again the second call will report that the subscription is already
        # active.
        evt2 = api.watch_address(addy2, cb1)
        if 'code' in evt2 and evt2['code'] == 409:
            # See comment above.
            evt2 = evt1.copy()
            evt2['address'] = addy2
        else:
            self.fail('unexpected behavior: %r' % evt2)

        self.assertEqual(evt1['id'], evt2['id'])
        self.assertNotEqual(evt1['address'], evt2['address'])

    def _check_watchaddress(self, res, cb, address):
        self.assertIn('id', res)
        self.evt_list.add(res['id'])
        self.assertEqual(res.get('success'), True)
        self.assertEqual(res.get('callback'), cb)
        self.assertEqual(res.get('address'), address)
        self.assertEqual(res.get('type'), 'address')

    def _check_watchblock(self, res, cb, etype):
        self.assertIn('id', res)
        self.evt_list.add(res['id'])

        self.assertEqual(res.get('success'), True)
        self.assertEqual(res.get('callback'), cb)
        self.assertEqual(res.get('type'), etype)


def _get_txid(blockheight):
    block = api.query(blockheight)
    for tx in block['data']['rawtx']:
        txid = tx['txid']
        return txid


def _get_address(blockheight):
    block = api.query(blockheight)
    for tx in block['data']['rawtx']:
        for vout in tx['vout']:
            if 'addresses' in vout.get('scriptPubKey', ''):
                addr = vout['scriptPubKey']['addresses'][0]
                return addr


if __name__ == "__main__":
    unittest.main(verbosity=2)
