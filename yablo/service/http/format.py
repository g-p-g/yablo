def strip_transaction(tx):
    del tx['hex']
    del tx['confirmations']
    for txin in tx['vin']:
        txin.pop('scriptSig', '')
        txin.pop('coinbase', '')
    for txout in tx['vout']:
        txout['scriptPubKey'].pop('hex')
        txout['scriptPubKey'].pop('asm')
