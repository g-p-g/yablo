import sys

from klein import route, run
from twisted.python import log
from twisted.internet import reactor


port = int(sys.argv[1])
custom_route = sys.argv[2]
reqcount = 0


@route('/%s' % custom_route, methods=["POST"])
def watch(request):
    global reqcount
    reqcount += 1
    log.msg(str(request.content.read()))
    return str(reqcount)


@route('/count', methods=["GET"])
def count(request):
    return str(reqcount)


@route('/stop', methods=["GET"])
def stop(request):
    reactor.stop()
    return 'bye'


run("localhost", port)
