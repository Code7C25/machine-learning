import httpx
import time
import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from celery import group
from celery.result import GroupResult
from worker.celery_app import celery as celery_app
from config import COUNTRY_TO_SPIDERS

# --- CONFIGURACIÓN ---
app = FastAPI(title="Cheapy Scraper API - Async")
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DB_FILE = BASE_DIR / "cache.db"
CACHE_DURATION_SECONDS = 86400

# --- SETUP DB CACHÉ ---
def setup_cache_database():
    conn = sqlite3.connect(CACHE_DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ip_cache (ip TEXT PRIMARY KEY, country TEXT, timestamp REAL)")
    conn.commit()
    conn.close()
setup_cache_database()

# --- MIDDLEWARE ---
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- FUNCIÓN DE GEOLOCALIZACIÓN ---
def get_country_from_ip(ip: str) -> str:
    default_country = "AR"
    conn = sqlite3.connect(CACHE_DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT country, timestamp FROM ip_cache WHERE ip = ?", (ip,))
        result = cursor.fetchone()
        if result and (time.time() - result[1] < CACHE_DURATION_SECONDS): return result[0]
        response = httpx.get("https://ipapi.co/json/", timeout=3.0)
        response.raise_for_status()
        data = response.json()
        country_code = data.get("country_code")
        if country_code:
            country_code = country_code.upper()
            cursor.execute("INSERT OR REPLACE INTO ip_cache VALUES (?, ?, ?)", (ip, country_code, time.time()))
            conn.commit()
            return country_code
        return default_country
    except Exception: return default_country
    finally: conn.close()

# --- ENDPOINTS (MODIFICADOS) ---

@app.get("/buscar")
def buscar_producto(q: str, request: Request, country: str = None):
    """
    Busca un producto. Prioriza el país enviado por el cliente.
    Si no se envía, usa geolocalización por IP como fallback.
    """
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    country_code = ""
    if country:
        # Si el frontend envía un país, lo usamos.
        country_code = country.upper()
        print(f"API: País '{country_code}' recibido del frontend.")
    else:
        # Si no, usamos la geolocalización del backend como fallback.
        print("API: No se recibió país del frontend. Usando geolocalización por IP...")
        client_ip = request.client.host
        country_code = get_country_from_ip(client_ip)
    
    # --- MODO DE PRUEBA (OPCIONAL) ---
    # Para forzar un país durante el desarrollo, puedes sobreescribir la variable aquí.
    #country_code = "MX"
    
    spiders_to_run = COUNTRY_TO_SPIDERS.get(country_code, [])
    if not spiders_to_run:
        return {"task_id": None, "error": f"No hay tiendas para tu región ({country_code})."}

    print(f"API: Tarea recibida para '{q}' en '{country_code}'. Spiders: {spiders_to_run}")

    task_signatures = [
        celery_app.signature(
            'run_scrapy_spider_task', 
            kwargs={'store_name': name, 'query': q, 'country': country_code} # <-- ¡CAMBIO AQUÍ!
        )
        for name in spiders_to_run
    ]
    result_group = group(task_signatures).apply_async()
    result_group.save()
    return {"task_id": result_group.id}


@app.get("/resultados/{task_id}")
def get_status(task_id: str):
    result_group = GroupResult.restore(task_id, app=celery_app)
    if not result_group: return {"status": "FAILURE", "error": "ID de tarea no encontrado."}
    if result_group.failed(): return {"status": "FAILURE", "error": "Al menos una tarea falló."}

    if result_group.ready():
        # --- ¡CORRECCIÓN IMPORTANTE AQUÍ! ---
        # Aplanamos la lista de listas en una sola lista de resultados.
        results_from_worker_group = result_group.get(propagate=False)
        print(f"[API] Resultados recuperados de Redis. {len(results_from_worker_group)} tareas del grupo respondieron.")
        
        all_results = [item for sublist in results_from_worker_group if sublist for item in sublist]

        # El resto de la lógica de procesamiento no cambia
        final_results = []
        seen_urls = set()
        for item in all_results:
            if isinstance(item, dict):
                url = item.get("url")
                if url and url not in seen_urls and isinstance(item.get("price_numeric"), (int, float)):
                    seen_urls.add(url)
                    final_results.append(item)
        
        final_results.sort(key=lambda x: (-x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))
        return {"status": "SUCCESS", "results": final_results}
    else:
        return {"status": "PENDING", "completed": f"{result_group.completed_count()}/{len(result_group)}"}