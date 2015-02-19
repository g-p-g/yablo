import os
import sys
import time
import atexit
import tempfile

from helper import Node


def dirname():
    count = 0
    temp = tempfile.gettempdir()
    while True:
        count += 1
        yield os.path.join(temp, 'forker', 's%d' % count)


def stop_nodes(nodelist):
    print 'stopping nodes: %r' % nodelist
    for node in nodelist:
        node.stop()
    print 'stopped'


nodes = []
datadir = dirname()
atexit.register(lambda: stop_nodes(nodes))


# Start a node.
datadir1 = next(datadir)
rpcport1 = int(sys.argv[1]) if len(sys.argv) > 1 else 20000
listenport1 = 25000
node1 = Node(datadir1, rpcport1, listenport1, name='node 1')
nodes.append(node1)
node1.start()

# Start btcwallet, create a wallet and get new addresses.
node_wallet = Node(datadir1, rpcport1, 21000, name='wallet', wallet=True,
                   rmtree=False)
nodes.append(node_wallet)
node_wallet.start()
node_wallet.runcmd(['createencryptedwallet', 'xyz'])
address1 = node_wallet.runcmd('getnewaddress')[0].strip()
address2 = node_wallet.runcmd('getnewaddress')[0].strip()
if address1 is None or address2 is None:
    raise Exception('Failed to create wallet')
print address1
print address2


# Start a second node for mining blocks that is connected to the first node.
rpcport2 = rpcport1 + 1
listenport2 = listenport1 + 1
node2 = Node(next(datadir), rpcport2, listenport2, name='node 2',
             mining=address1, connectport=listenport1)
nodes.append(node2)
node2.start()


# Start a third node for mining blocks with the intention to create a fork.
rpcport3 = rpcport2 + 1
listenport3 = listenport2 + 1
node3 = Node(next(datadir), rpcport3, listenport3, name='node 3',
             connectport=listenport1, mining=address2)
nodes.append(node3)
node3.start()


# Start a fourth node that will sync with the third one only.
rpcport4 = rpcport3 + 1
listenport4 = listenport3 + 1
node4 = Node(next(datadir), rpcport4, listenport4, name='node 4',
             connectport=listenport3)
nodes.append(node4)
node4.start()


# Disconnect the third node from the first one.
time.sleep(1)
node3.disconnect(node1)


# Start mining and polling for the current block count in node 2.
node2.mining(True)
blockcount = 0
while blockcount <= 100:
    blockcount = int(node2.runcmd('getblockcount')[0].strip())
    print blockcount
    if blockcount > 100:
        break
    time.sleep(0.001)
# Stop mining on node 2.
node2.mining(False)

# Wait sync with node 1. Actually this is something that resembles
# a sync as there is no guarantee it is in fact synced.
difficulty, nblocks = node1.waitblocks(101)
print difficulty
print "Syncing done"


# Disconnect the second node from the first one.
time.sleep(1)
node2.disconnect(node1)


# Create a fork by mining on the third node which is connected only
# to the fourth one.
node3.mining(True)
new_difficulty = difficulty
new_blockcount = 0
while new_difficulty <= difficulty:
    new_difficulty = float(node3.runcmd('getdifficulty')[0].strip())
    print new_difficulty
node3.mining(False)


# Reconnect nodes and let the fork be noticed.
time.sleep(1)
node3.connect(node1)


difficulty, nblocks = node1.waitblocks(nblocks + 1)
print difficulty, nblocks
raw_input("Syncing done, press enter to quit")
