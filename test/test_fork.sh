HERE=$(cd $(dirname $0); pwd -P)
cd "$HERE"

python forker.py &
FPID=$!

cd .. && PYTHONPATH=. timeout 300 python test/fork_watcher.py
RESULT=$?

kill -2 ${FPID}
wait ${FPID}

echo "result: ${RESULT}"
exit ${RESULT}
