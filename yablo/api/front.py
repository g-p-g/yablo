"""
Receive requests from some frontend and send them to
be processed somewhere else.
"""
import json
from urlparse import urlparse

import treq
from klein import Klein
from twisted.python import log

from ..config import app_config


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
    try:
        query_url = '%s/%s' % (QUERY_SERVER_URL, query_request)
    except Exception:
        log.err()
        query_request = None

    if query_request:
        result = treq.get(query_url)
        result.addCallback(treq.content)
    else:
        result = '{"error": "query not specified"}'

    return result


@app.route('/watch/<addy>', methods=["POST"])
def watch(request, addy):
    request.setHeader("Access-Control-Allow-Origin", '*')

    new_watch = {}
    if addy not in ('newblocks', 'newblock'):
        if not (26 <= len(addy) <= 35):
            # Consider actually checking for a valid address here.
            return '{"error": "invalid address"}'
        new_watch['address'] = addy
        url_append = '/address'
    else:
        url_append = '/newblock'

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


resource = app.resource
