"""
Process /watch requests.
"""
import json
from uuid import uuid4
from datetime import datetime

from klein import Klein
from sqlalchemy.orm.exc import NoResultFound

from ..error import ErrorFrontend
from ..storage.sql_db import setup_storage, get_or_create, create_if_not_present
from ..storage.sql_db import (WatchAddress, Subscriber, SubscriberNewBlock,
                              SubscriberWatchAddress, WebhookSubscriber)


storage = setup_storage()
app = Klein()


@app.route('/watch/address', methods=['POST'])
def watch_address(request):
    body = json.loads(request.content.read())
    addy = body['address']
    webhook = body['callback']

    session = storage()

    # Associate the subscriber with a watch address.
    hook_subs = _find_create_hooksubscriber(session, webhook)
    watch = get_or_create(session, WatchAddress, address=addy)
    subs_watch = create_if_not_present(session, SubscriberWatchAddress,
                                       subscriber=hook_subs.subscriber,
                                       address=watch)

    if subs_watch:
        session.add_all([watch, subs_watch])
        session.commit()
        result = {
            "id": hook_subs.subscriber.public_id,
            "type": "address",
            "callback": webhook,
            "address": addy,
            "success": True
        }
    else:
        result = {"success": False}
        result.update(ErrorFrontend.err_already_exists)

    return json.dumps(result)


@app.route('/watch/newblock')
def watch_newblock(request):
    body = json.loads(request.content.read())
    webhook = body['callback']

    session = storage()

    # Associate the subscriber with the newblock event.
    hook_subs = _find_create_hooksubscriber(session, webhook)
    subs_newblock = create_if_not_present(session, SubscriberNewBlock,
                                          subscriber=hook_subs.subscriber)
    if subs_newblock:
        session.add(subs_newblock)
        session.commit()
        result = {
            "id": hook_subs.subscriber.public_id,
            "type": "newblock",
            "callback": webhook,
            "success": True
        }
    else:
        result = {"success": False}
        result.update(ErrorFrontend.err_already_exists)

    return json.dumps(result)


def _find_create_hooksubscriber(session, webhook):
    try:
        hook_subs = session.query(WebhookSubscriber).filter_by(
            hook=webhook).one()
    except NoResultFound:
        # For now authorization for webhooks is not used. This would
        # prevent people from registering webhooks to URLs they don't
        # control.
        subscriber = Subscriber(public_id=str(uuid4()))
        hook_subs = WebhookSubscriber(
            hook=webhook,
            auth_path='', authorized=datetime.utcnow(),
            subscriber=subscriber)
        session.add_all([subscriber, hook_subs])
        session.flush()

    return hook_subs


resource = app.resource
