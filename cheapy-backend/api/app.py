 # cheapy-backend/api/app.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from celery.result import AsyncResult
# Solo importamos la instancia de Celery, no la tarea específica
from worker.celery_app import celery as celery_app

app = FastAPI(title="Cheapy Scraper API - Async")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

@app.get("/buscar")
def buscar_producto(q: str, country: str = "AR"):
    print(f"API: Tarea recibida para buscar '{q}' en '{country}'. Enviando al worker...")
    
    # --- ¡CAMBIO IMPORTANTE! ---
    # Enviamos la tarea usando su nombre explícito.
    task = celery_app.send_task(
        'run_scrapy_spider_task', # <-- Usamos el nombre que definimos en el decorador
        kwargs={'query': q, 'country': country.upper()}
    )
    
    return {"task_id": task.id}

@app.get("/resultados/{task_id}")
def get_status(task_id: str):
    task_result = AsyncResult(task_id, app=celery_app)
    
    if task_result.failed():
        # Si la tarea falló, podemos ver el error.
        print(f"API: Tarea {task_id} falló.")
        return {"status": "FAILURE", "error": str(task_result.result)}

    if task_result.ready():
        print(f"API: Tarea {task_id} está lista. Devolviendo resultados.")
        return {"status": "SUCCESS", "results": task_result.get()}
    else:
        print(f"API: Tarea {task_id} aún no está lista. Estado: {task_result.state}")
        return {"status": task_result.state}