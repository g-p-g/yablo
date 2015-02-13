import os
from ConfigParser import ConfigParser

from . import error

__all__ = ["parse_config", "app_config"]


expand = lambda p: os.path.abspath(os.path.expanduser(p))

app_config = {}


def parse_config(fpath, assume_defaults=True):
    cfg = ConfigParser()
    cfg.readfp(open(expand(fpath)))

    app_config.update(dict(cfg.items('yablo')))
    _parse_bitcoin(dict(cfg.items('bitcoind')), assume_defaults=assume_defaults)
    _parse_db(dict(cfg.items('database')), assume_defaults=assume_defaults)


def _parse_bitcoin(cfg, assume_defaults):
    if 'bitcoin_conf' not in cfg and not assume_defaults:
        raise error.ConfigException("Provide a path for bitcoin_conf")

    err = _parse_btcd(cfg, assume_defaults)
    app_config['bitcoin_cfg'] = False if err else True


def _parse_btcd(cfg, assume_defaults):
    if 'rpc_cert' not in cfg and not assume_defaults:
        raise error.ConfigException("Provide the path for the rpc_cert setting")

    cert = expand(cfg.get('rpc_cert', '~/.btcd/rpc.cert'))
    app_config['bitcoin_cert'] = cert

    confpath = cfg.get('bitcoin_conf', '~/.btcd/btcd.conf')
    btcd_cfg = ConfigParser()
    try:
        btcd_cfg.readfp(open(expand(confpath)))
    except IOError:
        # btcd config could not be read, assuming it is not
        # required. Otherwise, this will fail when trying to
        # use it.
        return True

    rawcfg = dict(btcd_cfg.items('Application Options'))
    if 'rpclisten' not in rawcfg and cfg.get('port'):
        rawcfg['rpclisten'] = cfg['port']
    _parse_bitcoin_common(rawcfg, assume_defaults, 1)


def _parse_bitcoin_common(rawcfg, assume_defaults, add_port):
    use_default = False
    testnet = int(rawcfg.get('testnet', '0'))
    if 'rpcserver' not in rawcfg:
        rawcfg['rpcserver'] = 'localhost'
        use_default = True
    if 'rpclisten' not in rawcfg:
        rawcfg['rpclisten'] = (8333 if not testnet else 18333) + add_port
        use_default = True
    else:
        rawcfg['rpclisten'] = int(rawcfg['rpclisten'])

    if assume_defaults and not use_default:
        raise error.ConfigException("bitcoin_conf: Provide a server "
                                    "(rpcserver) and port to connect to (rpclisten)")

    app_config.update(rawcfg)


def _parse_db(cfg, assume_defaults):
    key_prefix = cfg.get('key_prefix')
    if key_prefix is None and not assume_defaults:
        raise error.ConfigException("No value defined for 'key_prefix'")

    conn_string = cfg.get('conn_string')
    if conn_string is None:
        try:
            conn_string = os.environ['DB_CONNECTION']
        except KeyError:
            raise error.ConfigException('Database connection string not defined')

    app_config['conn_string'] = conn_string
    app_config['conn_evt_string'] = cfg.get('conn_evt_string', conn_string)
    app_config['key_prefix'] = key_prefix or 'yab'
