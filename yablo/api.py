import requests

from .config import app_config


BASE_URL = app_config['front_server']


def query(term):
    """
    Search for a txid, block (by height or hash), address,
    or best block.

    :param str term: specify what you are looking for
    :rtype: dict
    """
    response = requests.get(BASE_URL, params={'q': term})
    return response.json()


def watch_address(address, webhook):
    """
    Start watching for transactions involving the specified address.

    :param str address: the address to watch
    :param str webhook: the http(s) url that will receive POST
        requests describing the event involving the address specified
    :rtype: dict
    """
    response = requests.post(BASE_URL + "/watch",
                             data={'address': address, 'callback': webhook})
    return response.json()


def watch_newblocks(webhook):
    """
    Start watching for new blocks.

    :param str webhook: the http(s) url that will receive POST
        requests describing the newblock event
    :rtype: dict
    """
    return watch_address('newblock', webhook)


def watch_discblock(webhook):
    """
    Start watching for blocks that are removed from the main chain.

    :param str webhook: the http(s) url that will receive POST
        requests describing the discblock event
    :rtype: dict
    """
    return watch_address('discblock', webhook)


def cancel_watch(watch_id):
    """
    Stop watching a given event.

    :param str watch_id: the id received from an earlier watch call
    :rtype: dict
    """
    response = requests.post(BASE_URL + "/watch/cancel",
                             data={'id': watch_id})
    return response.json()
