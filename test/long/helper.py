import os
import time
import errno
import shutil
import subprocess

__all__ = ['Node', 'DEVNULL']


DEVNULL = open(os.devnull, 'wb')

# Names for the executables.
BTCD = "btcd"
BTCCTL = "btcctl"
BTCWALLET = "btcwallet"


def btcd_params(datadir, rpcport, listenport, rpcuser='abc', rpcpass='def',
                connectport=None, mining=None):
    params = [
        "-C", "noname", "--simnet", "--notls",
        "--logdir=%s" % datadir, "--listen=127.0.0.1:%d" % listenport,
        "--rpcuser=%s" % rpcuser, "--rpcpass=%s" % rpcpass,
        "--datadir=%s" % datadir, "--rpclisten=127.0.0.1:%d" % rpcport
    ]
    if connectport:
        params += ['--connect=127.0.0.1:%d' % connectport]
    if mining:
        params += ['--miningaddr=%s' % mining]
    return params


def btcwallet_params(datadir, rpcport, rpcportlisten,
                     rpcuser='abc', rpcpass='def'):
    return [
        "-C", "noname", "--simnet", "--noclienttls", "--noservertls",
        "--logdir=%s" % datadir, "--datadir=%s" % datadir,
        "--username=%s" % rpcuser, "--password=%s" % rpcpass,
        "--rpcconnect=127.0.0.1:%d" % rpcport,
        "--rpclisten=127.0.0.1:%d" % rpcportlisten
    ]


def btcctl_params(rpcport, rpcuser='abc', rpcpass='def'):
    params = [
        "-C", "noname", "--simnet", "--notls",
        "--rpcuser=%s" % rpcuser, "--rpcpass=%s" % rpcpass,
        "--rpcserver=127.0.0.1:%d" % rpcport
    ]
    return params


def btcctl_cmd(params, command, attempts=20):
    if isinstance(command, basestring):
        command = [command]

    retcode = 1
    ctl_out, ctl_err = None, None
    while retcode and attempts:
        attempts -= 1
        btcctl = subprocess.Popen([BTCCTL] + params + command,
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        ctl_out, ctl_err = btcctl.communicate()
        retcode = btcctl.returncode
        if retcode:
            time.sleep(1)

    return ctl_out, ctl_err


class Node(object):

    def __init__(self, datadir, rpcport, listenport, name, wallet=False,
                 rmtree=True, **kwargs):
        self.datadir = datadir
        self.rpcport = rpcport
        self.listenport = listenport
        self.name = name or ''
        self.wallet = wallet
        self._rmtree = rmtree
        self.kwargs = kwargs

        self.ctlparams = None
        self.proc = None

    def __repr__(self):
        return 'Node(name="%s")' % self.name

    def start(self):
        if not self.wallet:
            params = [BTCD] + btcd_params(self.datadir, self.rpcport,
                                          self.listenport, **self.kwargs)
            self.ctlparams = btcctl_params(self.rpcport)
        else:
            params = [BTCWALLET] + btcwallet_params(self.datadir,
                                                    self.rpcport,
                                                    self.listenport)
            self.ctlparams = btcctl_params(self.listenport)

        try:
            self.proc = subprocess.Popen(params,
                                         stdout=DEVNULL, stderr=DEVNULL)
            if self.name:
                print 'Starting %s...' % self.name
            if not self.wallet:
                # Check that it's running by issuing the getinfo command.
                print self.runcmd('getinfo')
        except:
            self.stop()
            raise

    def stop(self, rmtree=None):
        if self.ctlparams:
            self.runcmd('stop')
        elif self.proc:
            self.proc.terminate()
        self.proc = None
        self.ctlparams = None

        if rmtree is None:
            # No action specified, decide to remove the directory
            # based on _rmtree
            rmtree = self._rmtree
        if not rmtree:
            return

        try:
            print 'Removing %s' % self.datadir
            shutil.rmtree(self.datadir)
        except OSError, err:
            # Raise the error unless it was due to the dir not existing.
            if err.errno != errno.ENOENT:
                raise

    def runcmd(self, cmd):
        return btcctl_cmd(self.ctlparams, cmd)

    def disconnect(self, node):
        """Disconnect this node from another node."""
        print "Disconnecting %s from %s" % (self.name, node.name)
        return self.runcmd(['addnode', '127.0.0.1:%d' % node.listenport, 'remove'])

    def connect(self, node):
        print "Connecting %s to %s" % (self.name, node.name)
        return self.runcmd(['addnode', '127.0.0.1:%d' % node.listenport, 'add'])

    def mining(self, start):
        self.runcmd(['setgenerate', str(int(start))])
        if start:
            print "Start mining on %s" % self.name
        else:
            print "Stop mining on %s" % self.name

    def waitblocks(self, count_target):
        print "Waiting for blocks in %s.." % self.name
        last_blockcount = -1
        while True:
            blockcount = int(self.runcmd('getblockcount')[0].strip())
            print blockcount, count_target
            if blockcount > count_target:
                last_blockcount = blockcount
                break
            time.sleep(1)
        difficulty = float(self.runcmd('getdifficulty')[0].strip())
        return difficulty, last_blockcount
