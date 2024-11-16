
#! /usr/bin/env bash
set -e

# Create logs directory if it doesn't exist
mkdir -p /app/logs

python app/celery_app/pre_celery_start.py


celery -A app.celery_app worker -n database_handler -l info  -f logs/database.logs -Q db_queue
