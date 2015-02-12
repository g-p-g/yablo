"""
Listen for events in the network and store them as necessary.
"""
import logging

import redis

from yablo.service.btcd_ws import BitcoinWebsocket


def main():
    logging.basicConfig(format='%(levelname)s [%(asctime)s] (%(funcName)s @ %(name)s): %(message)s',
                        level=logging.DEBUG)

    red = redis.StrictRedis()
    cli = BitcoinWebsocket(red)
    cli.setup()

    cli.logger.debug('waiting for notifications..')
    handler = cli.handle_message()
    while True:
        cli.logger.debug('next!')
        next(handler)


if __name__ == "__main__":
    main()
