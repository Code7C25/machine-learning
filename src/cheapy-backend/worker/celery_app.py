from celery import Celery

celery = Celery(
    'cheapy_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['worker.tasks']
)

celery.conf.update(
    task_track_started=True,
)