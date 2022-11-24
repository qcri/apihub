#!/bin/bash

# Defining variables
HOST1="http://0.0.0.0:8099"
HOST2="http://0.0.0.0:5000"

function locust_caller {

  if [[ -n "$2" ]] && [[ "$2" = "ignore" ]]; then
    locust --locustfile "$1" --users "$USERS" --spawn-rate "$SPAWN_RATE" --host "$HOST" --run-time "$RUN_TIME" --only-summary  --loglevel ERROR --headless
  else
    locust --locustfile "$1" --users "$USERS" --spawn-rate "$SPAWN_RATE" --host "$HOST" --run-time "$RUN_TIME" --only-summary --loglevel ERROR --headless &>>"$OUTPUT_FILE"
  fi
}

RUN_TIME=5
USERS=1
SPAWN_RATE=1
#locust_caller "/app/performance_testing/locustfile.py" "ignore"

locust --locustfile "/app/locustfiles/locustfile.py" --users "$USERS" --spawn-rate "$SPAWN_RATE" --host "$HOST1" --run-time "$RUN_TIME" --only-summary  --loglevel ERROR --headless
locust --locustfile "/app/locustfiles/locustfile.py" --users "$USERS" --spawn-rate "$SPAWN_RATE" --host "$HOST2" --run-time "$RUN_TIME" --only-summary  --loglevel ERROR --headless

