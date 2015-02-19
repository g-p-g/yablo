HERE=$(cd $(dirname $0); pwd -P)
cd "$HERE"

python forker.py &
FPID=$!

# Pseurandom route for receiving requests.
ROUTE=$(dd if=/dev/urandom bs=1 count=8 2>/dev/null | xxd -p)
PORT=12312

# Start http server for listening for callbacks.
python receiver.py ${PORT} ${ROUTE} &

cd ../.. && PYTHONPATH=. timeout 300 python test/long/fork_watcher_integration.py ${PORT} ${ROUTE}
RESULT=$?

# Stop http server started earlier.
STOP_LISTEN="http://localhost:${PORT}/stop"
curl -X GET ${STOP_LISTEN}

kill -2 ${FPID}
wait ${FPID}

echo "result: ${RESULT}"
exit ${RESULT}
