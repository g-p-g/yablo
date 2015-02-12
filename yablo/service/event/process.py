import json
import logging
import calendar
from uuid import uuid4
from datetime import datetime

from ...error import YabloException
from ...config import app_config
from ...storage import redis_keys
from ...storage.sql_db import setup_storage
from ...storage.sql_db import (WatchAddress, WebhookSubscriber, Event,
                               SubscriberWatchAddress, SubscriberNewBlock)


EVENT_TYPE = {
    redis_keys.EVENT_WATCH_BLOCK: 'newblock',
    redis_keys.EVENT_WATCH_ADDR: 'address'
}


# Mapping for decoding keys used to store a transaction in redis.
TRANS_MAPPING = {
    'i': 'input', 'o': 'output', 'a': 'address',
    'v': 'value', 'c': 'confirmations',
    'b': 'block_hash', 't': 'txid'
}

# Mapping for decoding keys used to store a block in redis.
BLOCK_MAPPING = {
    'b': 'block_hash', 'd': 'difficulty',
    'p': 'previousblockhash', 'h': 'height',
    'ts': 'time', 'tx': 'tx'
}


def process_event(red, db, evt):
    """
    Record and send events to registered webhooks.
    """
    evt_type = evt.pop('type')
    data = evt.pop('data')
    if evt_type == redis_keys.EVENT_NEW_TRANS:
        num = _process_new_trans(red, db, data)
    elif evt_type == redis_keys.EVENT_NEW_BLOCK:
        num = _process_new_block(red, db, data)
    elif evt_type == redis_keys.EVENT_BLOCKDISC:
        num = _process_blockdisc(red, db, data)
    else:
        raise YabloException("unknown event type '%s'" % evt_type)

    return num


def _process_new_trans(red, db, raw):
    trans, addresses = _format_trans(raw)

    # Find subscribers that are watching for one or more addresses
    # involved in this transaction.
    hooks = db.query(WebhookSubscriber, WatchAddress.address).\
        join(SubscriberWatchAddress,
             WebhookSubscriber.subs_id == SubscriberWatchAddress.subs_id).\
        join(WatchAddress,
             WatchAddress.addr_id == SubscriberWatchAddress.addr_id).\
        filter(WebhookSubscriber.active == True,
               WebhookSubscriber.authorized != None,  # noqa
               WatchAddress.address.in_(addresses)).all()
    if not hooks:
        return 0

    custom = {}
    subscribers = []
    for subs, addy in hooks:
        custom[subs] = {'address': addy}
        subscribers.append(subs)
    _store_dispatch(red, db, trans, redis_keys.EVENT_WATCH_ADDR,
                    custom, *subscribers)
    return len(subscribers)


def _process_new_block(red, db, raw):
    block = _format_block(raw)

    # Find subscribers that are watching for new blocks.
    subs = db.query(WebhookSubscriber).\
        join(SubscriberNewBlock,
             WebhookSubscriber.subs_id == SubscriberNewBlock.subs_id).\
        filter(WebhookSubscriber.active == True,
               WebhookSubscriber.authorized != None).all()  # noqa

    if subs:
        _store_dispatch(red, db, block, redis_keys.EVENT_WATCH_BLOCK,
                        {}, *subs)

    return len(subs)


def _process_blockdisc(red, db, raw):
    print raw, 'block disconnected :/'
    raise NotImplementedError


def _store_dispatch(red, db, data, etype, custom, *subscribers):
    origin_time = datetime.utcnow()
    event = {
        'type': EVENT_TYPE[etype],
        'data': data,
        'origin_time': calendar.timegm(origin_time.utctimetuple())
    }

    new_evt = []
    hook = []
    for subs in subscribers:
        event['id'] = subs.subscriber.public_id
        event['data']['event_id'] = str(uuid4())
        event.update(custom.get(subs, {}))
        hook.append(subs.hook)

        db_evt = Event(subs_id=subs.subs_id,
                       num_attempt=0,
                       data=json.dumps(event))
        new_evt.append(db_evt)

    db.add_all(new_evt)
    db.commit()

    for evt, webhook in zip(new_evt, hook):
        # Store the id for this event, which is ready to be sent.
        red.rpush(redis_keys.SEND_EVENT, '%d_%d' % (
            redis_keys.EVENT_METHOD_WEBHOOK, evt.evt_id))


def _format_trans(raw):
    trans = {}
    for key, val in raw.iteritems():
        new_key = TRANS_MAPPING[key]
        trans[new_key] = val

    # Format inputs / outputs.
    addresses = set([])
    for side in ('input', 'output'):
        for entry in trans[side]:
            for key in entry.keys():
                val = entry.pop(key)
                if key == 'a':
                    addresses.update(val)
                new_key = TRANS_MAPPING[key]
                entry[new_key] = val

    return trans, addresses


def _format_block(raw):
    block = {}
    for key, val in raw.iteritems():
        new_key = BLOCK_MAPPING[key]
        block[new_key] = val
    return block


def process_loop(red, cfg=None):
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())

    storage = setup_storage(conn_string=(cfg or app_config)['conn_evt_string'])
    session = storage()

    # Move unfinished requests around so they are retried.
    # Right now this is the only time this is done, so you
    # might need to run this elsewhere to retry processing
    # events (better yet, investigate why that is happening).
    while red.rpoplpush(redis_keys.HANDLE_EVENT_TEMP,
                        redis_keys.HANDLE_EVENT):
        pass

    while True:
        logger.debug('waiting for events')
        evt = red.brpoplpush(redis_keys.HANDLE_EVENT,
                             redis_keys.HANDLE_EVENT_TEMP)
        logger.debug('got event: %r', evt)

        try:
            num = process_event(red, session, json.loads(evt))
            logger.debug('notifications scheduled: %d' % num)
            red.lrem(redis_keys.HANDLE_EVENT_TEMP, -1, evt)
        except Exception, e:
            logger.exception(e)
