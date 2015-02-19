# -*- encoding: utf-8 -*-
import unittest

from yablo import api


class TestQuery(unittest.TestCase):

    def test_query_notspecified(self):
        for notspecified in (None, ''):
            res = api.query(notspecified)
            self.assertIn('error', res)
            self.assertEqual(res['error'], 'query not specified')

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
        self.assertGreater(res['data']['confirmations'], 0)

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
    unittest.main()
