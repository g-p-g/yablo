"""
Event processor.
"""
import sys
import logging

import redis

from yablo.service.event.process import process_loop


def main(pnum):
    logformat = '%(levelname)s [%(asctime)s] %(funcName)s: %(message)s'
    if pnum is not None:
        logformat = ('%s -> ' % pnum) + logformat
    logging.basicConfig(format=logformat, level=logging.DEBUG)

    red = redis.StrictRedis()

    process_loop(red)


if __name__ == "__main__":
    process_num = sys.argv[1] if len(sys.argv) == 2 else None
    main(process_num)
