
#! /usr/bin/env bash
set -e

# Create logs directory if it doesn't exist
mkdir -p /app/logs

python app/celery_app/pre_celery_start.py

# start the worker for executing tasks
celery -A app.celery_app worker -l info  -f logs/database.logs

# starts the beat worker
celery -A app.celery_app beat -l info -f logs/celerybeat.logs -s /celerybeat-schedule

