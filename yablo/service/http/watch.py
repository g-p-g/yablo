"""
Process /watch requests.
"""
import json
from uuid import uuid4
from datetime import datetime

from klein import Klein
from sqlalchemy.orm.exc import NoResultFound

from ...error import ErrorFrontend
from ...storage.sql_db import setup_storage, get_or_create, create_if_not_present
from ...storage.sql_db import (WatchAddress, Subscriber, SubscriberNewBlock,
                               SubscriberDiscBlock, SubscriberWatchAddress,
                               WebhookSubscriber)


storage = setup_storage()
app = Klein()


@app.route('/watch/address', methods=['POST'])
def watch_address(request):
    """
    Start watching a given address.
    """
    body = json.loads(request.content.read())
    addy = body['address']
    webhook = body['callback']

    session = storage()

    # Associate the subscriber with a watch address.
    hook_subs = _find_create_hooksubscriber(session, webhook)
    watch = get_or_create(session, WatchAddress, address=addy)
    subs_watch, created = create_if_not_present(session, SubscriberWatchAddress,
                                                subscriber=hook_subs.subscriber,
                                                address=watch)


    if not created and hook_subs.active:
        result = {"success": False}
        result.update(ErrorFrontend.err_already_exists)
    else:
        if not hook_subs.active:
            hook_subs.active = True
            session.add(hook_subs)
        if created:
            session.add(subs_watch)
        session.add(watch)
        session.commit()
        result = {
            "id": hook_subs.subscriber.public_id,
            "type": "address",
            "callback": webhook,
            "address": addy,
            "success": True
        }

    return json.dumps(result)


@app.route('/watch/newblock', methods=['POST'])
def watch_newblock(request):
    """
    Start watching for new blocks.
    """
    result = _simple_subscriber(request, 'newblock', SubscriberNewBlock)
    return json.dumps(result)


@app.route('/watch/discblock', methods=['POST'])
def watch_discblock(request):
    """
    Start watching for blocks that are removed from the main chain.
    """
    result = _simple_subscriber(request, 'discblock', SubscriberDiscBlock)
    return json.dumps(result)


@app.route('/watch/cancel', methods=['POST'])
def watch_cancel(request):
    """
    Stop watching a specific event.
    """
    body = json.loads(request.content.read())
    event_id = body['id']

    session = storage()
    try:
        hook_subs = session.query(WebhookSubscriber).\
            join(Subscriber, WebhookSubscriber.subs_id == Subscriber.subs_id).\
            filter(Subscriber.public_id == event_id,
                   WebhookSubscriber.active == True).one()  # noqa
    except NoResultFound:
        # The subscriber is no longer active or it never existed.
        result = {"success": False}
        result.update(ErrorFrontend.err_not_found)
    else:
        hook_subs.active = False
        session.commit()
        result = {"success": True}

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
            hook=webhook, active=True,
            auth_path='', authorized=datetime.utcnow(),
            subscriber=subscriber)
        session.add_all([subscriber, hook_subs])
        session.flush()

    return hook_subs


def _simple_subscriber(request, substype, model):
    body = json.loads(request.content.read())
    webhook = body['callback']

    session = storage()

    # Associate the subscriber with the newblock event.
    hook_subs = _find_create_hooksubscriber(session, webhook)
    subs_instance, created = create_if_not_present(session, model,
                                                   subscriber=hook_subs.subscriber)
    if not created and hook_subs.active:
        result = {"success": False}
        result.update(ErrorFrontend.err_already_exists)
    else:
        if not hook_subs.active:
            hook_subs.active = True
            session.add(hook_subs)
        if created:
            session.add(subs_instance)
        session.commit()
        result = {
            "id": hook_subs.subscriber.public_id,
            "type": substype,
            "callback": webhook,
            "success": True
        }

    return result


resource = app.resource
