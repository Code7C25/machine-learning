# cheapy-backend/worker/celery_app.py

from celery import Celery

# Creamos la instancia de Celery que será compartida por todos los componentes.
# Le damos un nombre al proyecto y le decimos que busque tareas en el módulo 'worker.tasks'.
celery = Celery(
    'cheapy_tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=['worker.tasks']
)

# Opcional: Configuración adicional para un mejor seguimiento
celery.conf.update(
    task_track_started=True,
)