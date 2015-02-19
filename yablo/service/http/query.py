"""
Process /query requests.
"""
import json
import difflib

import redis
from klein import Klein
from twisted.python import log

from .format import strip_transaction
from ..btcd_ws import BitcoinWebsocket
from ...storage.redis_db import RedisStorage


app = Klein()

red = redis.StrictRedis()
storage = RedisStorage(red)
btc = BitcoinWebsocket(red)
btc.setup(notifier=False)


@app.route('/query')
def handle_query(request):
    log.msg(repr(request.args))
    query = request.args.get('q')[0]

    # Return a cached version if it exists.
    cache = storage.cached_query(query)
    if cache:
        log.msg('cache hit', query)
        return cache
    else:
        log.msg('cache miss', query)

    result, cache_by = process_query(query)
    encres = json.dumps(result, sort_keys=True)

    # Cache the result.
    for key, val in cache_by.iteritems():
        result['query'] = [key]
        cache_key = query if val is None else result['data'][val]
        storage.cache_query(cache_key, json.dumps(result, sort_keys=True))

    return encres


def process_query(query):
    result = {'query': None, 'data': None}
    cache_by = None

    if query.isdigit() and len:
        # Query by block height.
        result['query'] = ['height']
        res = query_block_height(int(query))
        if res:
            # Found a block.
            result['data'] = res
            cache_by = {result['query'][0]: None, 'block_hash': 'hash'}
    elif len(query) == 64 and '_' not in query:
        # Try searching by txid first.
        result['query'] = ['txid']
        res = query_txid(query)
        if res:
            # Found a transaction.
            result['data'] = res
            cache_by = {result['query'][0]: None}
        else:
            # Try finding a block by its hash.
            result['query'].append('block_hash')
            res = query_block_hash(query)
            if res:
                result['data'] = res
                cache_by = {'block_hash': None, 'height': 'height'}
    elif 25 <= len(query) <= 35 and '_' not in query:
        result['query'] = ['address']
        result['data'] = query_address(query)
    else:
        # Spaces are replaced by "_" at the front-facing server.
        query_guess(result, query.replace('_', ' '))

    return result, cache_by or {}


def query_address(addy):
    btc.wss.send(method='validateaddress', params=[addy])
    info = btc.wss.recv()

    if not info['error'] and info['result']['isvalid']:
        # No errors occurred and this is a valid address.
        # XXX Search not implemented.
        return {
            'address': info['result']['address'],
            'note': 'not implemented'
        }


def query_guess(result, query):
    # XXX very poor implementation.
    valid = {
        'lastblock': set(['lastblock', 'bestblock'])
    }
    threshold = 0.8

    query = query.replace(' ', '').lower()
    match = (0, -1)
    for key, values in valid.iteritems():
        for entry in values:
            sim = difflib.SequenceMatcher(a=entry, b=query).ratio()
            log.msg("ratio(%s, %s) = %s" % (entry, query, sim))
            if sim > threshold and sim > match[0]:
                match = (sim, key)
                break

    if not match[0]:
        return

    result['query'] = ['custom', match[1]]
    # XXX this could be cached.
    result['data'] = query_block_height(0, bestblock=True)


def query_block_height(height, bestblock=False):
    """
    Return a block by its height.

    :param bool bestblock: if True, will ignore the heigh param
        and return the most recent block.
    """
    if height < 0:
        return

    if not bestblock:
        kwargs = {'method': 'getblockhash', 'params': [height]}
    else:
        kwargs = {'method': 'getbestblockhash'}
    btc.wss.send(**kwargs)
    blockhash = btc.wss.recv()

    if blockhash['result']:
        bhash = blockhash['result']
        return query_block_hash(bhash)


def query_block_hash(blockhash):
    try:
        int(blockhash, 16)
    except ValueError:
        return

    btc.wss.send(method='getblock', params=[blockhash, True, True])
    block = btc.wss.recv()

    if not block['result']:
        return

    del block['id']
    for tx in block['result']['rawtx']:
        strip_transaction(tx)

    return block['result']


def query_txid(txid):
    try:
        int(txid, 16)
    except ValueError:
        return

    btc.wss.send(method='getrawtransaction', params=[txid, 1])
    trans = btc.wss.recv()

    if not trans['result']:
        return

    tx = trans['result']
    strip_transaction(tx)
    return tx


resource = app.resource
