import sys
import json

from klein import route, run
from twisted.python import log
from twisted.internet import reactor

from yablo.checkjson import validate


port = int(sys.argv[1])
custom_route = sys.argv[2]
reqcount = 0


@route('/%s' % custom_route, methods=["POST"])
def watch(request):
    global reqcount
    reqcount += 1
    raw = request.content.read()
    log.msg(raw)
    validate(json.loads(raw))
    return str(reqcount)


@route('/count', methods=["GET"])
def count(request):
    return str(reqcount)


@route('/stop', methods=["GET"])
def stop(request):
    reactor.stop()
    return 'bye'


run("localhost", port)
