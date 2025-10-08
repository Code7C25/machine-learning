# api/app.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult

# --- CAMBIO 1: Importamos la instancia de Celery configurada ---
# Esto le da a nuestra API acceso a la configuración del broker y backend.
from worker.celery_app import celery as celery_app
from worker.tasks import run_scrapy_spider

app = FastAPI(title="Cheapy Scraper API - Async")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/buscar")
def buscar_producto(q: str, country: str = "AR"):
    """
    Inicia una tarea de scraping en segundo plano y devuelve un ID de tarea.
    """
    print(f"API: Tarea recibida para buscar '{q}' en '{country}'. Enviando al worker...")
    task = run_scrapy_spider.delay(query=q, country=country.upper())
    return {"task_id": task.id}

@app.get("/resultados/{task_id}")
def get_status(task_id: str):
    """
    Consulta el estado y el resultado de una tarea de scraping.
    """
    # --- CAMBIO 2: Le pasamos la app configurada a AsyncResult ---
    # Ahora, este objeto sabe que debe buscar los resultados en Redis.
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.ready():
        print(f"API: Tarea {task_id} está lista. Devolviendo resultados.")
        # El .get() ahora funcionará porque sabe cómo hablar con Redis
        return {"status": "SUCCESS", "results": task_result.get()}
    else:
        print(f"API: Tarea {task_id} aún no está lista. Estado: {task_result.state}")
        return {"status": task_result.state}