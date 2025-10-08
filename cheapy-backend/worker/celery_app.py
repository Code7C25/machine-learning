# worker/celery_app.py
from celery import Celery

# Creamos la instancia de Celery
# El primer argumento es el nombre del módulo actual.
# 'broker' es la URL de Redis, nuestro agente de mensajes.
# 'backend' es también Redis, donde guardaremos los resultados.
celery = Celery(
    'tasks',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Opcional: Configuración adicional
celery.conf.update(
    task_track_started=True,
)