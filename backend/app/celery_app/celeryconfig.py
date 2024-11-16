from celery.schedules import crontab
import os
import logging

task_serializer = "json"
enable_utc = False
timezone = "America/New_York"
worker_redirect_stdouts = True
worker_redirect_stdouts_level = "INFO"
task_track_started = True
task_ignore_result = False
broker_connection_retry_on_startup = True
# worker_concurrency = 8
broker_url = f"amqp://{os.getenv('RABBITMQ_DEFAULT_USER')}:{os.getenv('RABBITMQ_DEFAULT_PASS')}@{os.getenv('RABBITMQ_HOST')}:{os.getenv('RABBITMQ_PORT')}/{os.getenv('RABBITMQ_DEFAULT_VHOST')}"
result_backend = f"db+postgresql+psycopg2://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD').replace(' ','%20')}@{os.getenv('POSTGRES_SERVER')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
result_extended = True
celery_imports = ("tasks",)
