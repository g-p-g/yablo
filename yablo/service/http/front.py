"""
Receive requests from some frontend and send them to
be processed somewhere else.
"""
import json
from urlparse import urlparse

import treq
from klein import Klein
from twisted.python import log

from ...config import app_config


CORS_MAX_AGE = 60 * 60 * 24 * 5  # cache preflights for 5 days
QUERY_SERVER_URL = app_config['query_server']
WATCH_SERVER_URL = app_config['watch_server']

app = Klein()


@app.route('/', methods=["OPTIONS"])
def cors(request):
    request.setHeader("Access-Control-Allow-Origin", '*')
    request.setHeader("Access-Control-Allow-Methods", "GET, POST")
    request.setHeader("Access-Control-Max-Age", str(CORS_MAX_AGE))


@app.route('/', methods=["GET"])
def query(request):
    request.setHeader("Access-Control-Allow-Origin", '*')

    query_request = str(request.args.get('q', [''])[0].strip().replace(' ', '_'))
    log.msg('q> %r' % query_request)

    if query_request:
        result = treq.get(QUERY_SERVER_URL, params={'q': query_request})
        result.addCallback(treq.content)
    else:
        result = '{"error": "query not specified"}'

    return result


@app.route('/watch', methods=["POST"])
def watch(request):
    request.setHeader("Access-Control-Allow-Origin", '*')

    addy = str(request.args.get('address', [''])[0]).strip()
    log.msg('m> %r' % addy)

    new_watch = {}
    if addy in ('newblocks', 'newblock'):
        url_append = '/newblock'
    elif addy == 'discblock':
        url_append = '/discblock'
    else:
        # Watch an address.
        if not (26 <= len(addy) <= 35):
            # Consider actually checking for a valid address here.
            return '{"error": "invalid address"}'
        new_watch['address'] = addy
        url_append = '/address'

    webhook_raw = str(request.args.get('callback', [''])[0]).lower().strip()
    webhook = urlparse(webhook_raw)
    webhook_url = webhook.geturl()
    if not webhook.scheme or not webhook.netloc:
        return '{"error": "invalid callback \'%s\'"}' % webhook_url
    new_watch['callback'] = webhook_url

    result = treq.post(WATCH_SERVER_URL + url_append,
                       json.dumps(new_watch),
                       headers={'Content-Type': ['application/json']})
    result.addCallback(treq.content)
    return result


@app.route('/watch/cancel', methods=["POST"])
def watch_cancel(request):
    request.setHeader("Access-Control-Allow-Origin", '*')

    evt_id = str(request.args.get('id', [''])[0].strip())
    if len(evt_id) != 36:
        return '{"error": "invalid id \'%s\'"}' % evt_id

    result = treq.post(WATCH_SERVER_URL + '/cancel',
                       json.dumps({'id': evt_id}),
                       headers={'Content-Type': ['application/json']})
    result.addCallback(treq.content)
    return result


resource = app.resource
