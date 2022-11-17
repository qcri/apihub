#!/bin/bash

# Defining variables
#HOST="172.24.0.1:5000"
RUN_TIME=5
USERS=1
SPAWN_RATE=1
OUTPUT_FILE="performance_testing\logs.txt"

function locust_caller {

  if [[ -n "$2" ]] && [[ "$2" = "ignore" ]]; then
    locust --locustfile "$1" --users "$USERS" --spawn-rate "$SPAWN_RATE" --host "$HOST" --run-time "$RUN_TIME" --only-summary --loglevel ERROR --headless
  else
    locust --locustfile "$1" --users "$USERS" --spawn-rate "$SPAWN_RATE" --host "$HOST" --run-time "$RUN_TIME" --only-summary --loglevel ERROR &>>"$OUTPUT_FILE" --headless
  fi
}

locust_caller "./locust_test.py" "ignore"