# cheapy-backend/worker.py

import subprocess
import json
from celery import Celery

# 1. Damos un nombre de aplicación consistente: 'cheapy_tasks'
celery_app = Celery(
    'cheapy_tasks', # <-- CAMBIO AQUÍ
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# 2. Damos un nombre explícito a la tarea
@celery_app.task(name='run_scraper_task') # <-- AÑADE name='...'
def run_scraper_task(spider_name: str, query: str, country_code: str) -> list:
    # ... (el resto de la función no cambia) ...
    SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"
    command = [
        SCRAPY_PATH, "crawl", spider_name,
        "-a", f"query={query}", "-a", f"country={country_code}",
        "-o", "-:jsonlines"
    ]
    # ... (el resto del código de la tarea no cambia)
    # ...
    return raw_results