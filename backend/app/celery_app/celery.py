from celery import Celery
from app.celery_app import celeryconfig


app = Celery("worker", broker=celeryconfig.broker_url)

# # celery_instance.conf.update(include='app.tasks')
# celery_instance.conf.task_routes = {"celery_tasks": "main-queue4"}

app.config_from_object(celeryconfig)
app.autodiscover_tasks(packages=["app.celery_app.tasks"], force=True)
# celery_instance.autodiscover_tasks(packages=["celery_tasks"], force=True)


if __name__ == '__main__':
    app.start()