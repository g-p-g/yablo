"""
Event dispatcher.
"""
import sys
import logging

import redis

from yablo.event.dispatch import Dispatch


def main(pnum):
    logformat = '%(levelname)s [%(asctime)s] %(funcName)s: %(message)s'
    if pnum is not None:
        logformat = ('%s -> ' % pnum) + logformat
    logging.basicConfig(format=logformat, level=logging.DEBUG)

    red = redis.StrictRedis()

    dispatcher = Dispatch(red).handle_message()
    while True:
        next(dispatcher)


if __name__ == "__main__":
    process_num = sys.argv[1] if len(sys.argv) == 2 else None
    main(process_num)
