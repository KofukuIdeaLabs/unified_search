import logging
from celery.utils.log import get_task_logger
from backend.app.celery_app.celery import celery_instance

logger = get_task_logger(__name__)



@celery_instance.task(
    name="agents.execute", bind=True
)  # retry in 30 minutes
def execute_agent(self, data):
    # retrying the tasks
    try:
        pass
    except Exception as exc:
        logging.info("exception")
        logging.info(exc)
    return
