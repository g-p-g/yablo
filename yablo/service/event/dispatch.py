# Running more than one dispatch process at the same time is
# very likely to result in a single being delivered multiple
# times due to how rescheduling happens (i.e. if the recipients
# do not fail to receive the delivery of the events then this
# issue shouldn't be observed).

import random
import logging
from datetime import datetime

import requests
from sqlalchemy import or_
from sqlalchemy.orm.exc import NoResultFound

from ...config import app_config
from ...storage import redis_keys
from ...storage.sql_db import setup_storage, Event, WebhookSubscriber


REQUEST_CONNECT_TIMEOUT = 3  # seconds
REQUEST_READ_TIMEOUT = 3
REQUEST_TIMEOUT = (REQUEST_CONNECT_TIMEOUT, REQUEST_READ_TIMEOUT)


def dispatch_webhook(logger, db, evt_id):
    result = {'error': True, 'reason': 'unknown', 'retry': True}

    try:
        evt_hook = db.query(Event, WebhookSubscriber.hook).\
            join(WebhookSubscriber,
                 Event.subs_id == WebhookSubscriber.subs_id).\
            filter(Event.evt_id == evt_id, WebhookSubscriber.active == True,  # noqa
                   or_(Event.status == None, Event.status == 'retrying')).one()  # noqa
    except NoResultFound:
        result['retry'] = False
        result['reason'] = 'does not exist or was sent already'
        return result

    evt, hook = evt_hook
    evt.num_attempt += 1
    evt.last_attempt = datetime.utcnow()

    try:
        res = requests.post(hook, data=evt.data,
                            timeout=REQUEST_TIMEOUT,
                            headers={'Content-type': 'application/json'})
        if res and res.status_code == 200:
            result['error'] = False
            evt.status = 'sent'
        else:
            res.raise_for_status()
    except requests.exceptions.ReadTimeout:
        # Successfully connected to the remote server and sent all the
        # data, but it took too long to send a positive reply.
        # When this happens, it is assumed that the event has been sent
        # successfully.
        result['error'] = False
        evt.status = 'sent'
    except Exception, e:
        logger.exception(e)
        result['error'] = True
        result['reason'] = str(e)
        evt.status = 'retrying'
    finally:
        db.commit()

    return result


class Dispatch(object):

    def __init__(self, red, cfg=None):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(logging.NullHandler())

        self.red = red

        conn_string = (cfg or app_config)['conn_evt_string']
        storage = setup_storage(conn_string=conn_string)
        self.session = storage()

        self._reschedule_pending()

        # Initially, block indefinitely if there are no pending
        # events to be dispatched.
        self.block_seconds = 0

    def handle_message(self):
        """
        One infinite generator loop.
        """
        while True:
            result = self._process()
            yield result

    def _process(self):
        """
        :returns: True if the number of events to be dispatched got
            reduced. This is the case if one of them is sent sucessfully,
            or one of them is discarded.
        """
        self.logger.debug('waiting for events to dispatch')
        evt = self.red.brpoplpush(redis_keys.SEND_EVENT,
                                  redis_keys.SEND_EVENT_TEMP,
                                  self.block_seconds)
        if evt is None:
            # brpoplpush timed out.
            n = self._reschedule_pending()
            self.logger.debug('brpoplpush timeout - rescheduled %d', n)
            if n:
                # Something was rescheduled, let brpoplpush block
                # indefinitely again.
                self.block_seconds = 0
            return

        self.logger.debug('got event: %r', evt)
        return self._process_evt(evt)

    def _process_evt(self, evt):
        try:
            dispatch_method, sql_id = map(int, evt.split('_'))
            if dispatch_method == redis_keys.EVENT_METHOD_WEBHOOK:
                result = dispatch_webhook(self.logger, self.session, sql_id)
            else:
                # Invalid method, discard it.
                result = {
                    'error': True,
                    'retry': False,
                    'reason': "invalid dispatch method '%s'" % dispatch_method
                }

            if result and result['error']:
                if result['retry']:
                    raise Exception('failed to dispatch evt: %s' %
                                    repr(result['reason']))
                else:
                    self.logger.debug('discarding event %s: %s' % (
                        evt, result['reason']))

            self.red.lrem(redis_keys.SEND_EVENT_TEMP, -1, evt)
            # If there is nothing pending, block without a timeout.
            if not self.red.llen(redis_keys.SEND_EVENT_TEMP):
                self.logger.debug('reset block_seconds to 0')
                self.block_seconds = 0
            return True
        except Exception, e:
            self.logger.exception(e)
            # Next loop will wait at most n seconds for events.
            # If none are received, reschedule this task that failed
            # (and possibly others).
            self.block_seconds = random.randint(1, 3)
            self.logger.debug('set block_seconds to %d', self.block_seconds)

    def _reschedule_pending(self):
        """
        Move unfinished requests around so they are retried.

        :returns: the number of events rescheduled.
        """
        count = 0
        red = self.red
        while red.rpoplpush(redis_keys.SEND_EVENT_TEMP,
                            redis_keys.SEND_EVENT):
            count += 1
        return count
