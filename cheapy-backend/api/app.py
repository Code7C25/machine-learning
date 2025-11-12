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
        celery_app.signature('run_scrapy_spider_task', kwargs={'spider_name': name, 'query': q, 'country': country_code})
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
        print(f"[API] Contenido bruto de resultados_from_worker_group: {results_from_worker_group}")
        
        all_results = [item for sublist in results_from_worker_group if sublist for item in sublist]
        print(f"[API] Total de items después de aplanar: {len(all_results)}")

        # LOG: detectar items con reviews inusualmente grandes o con raw disponible
        try:
            for it in all_results:
                if isinstance(it, dict):
                    raw = it.get('reviews_count_raw')
                    parsed = it.get('reviews_count')
                    if parsed and parsed > 1000000:
                        print(f"[API] reviews_count grande detectado en item: parsed={parsed} raw={raw!r} title={it.get('title')!r} url={it.get('url')}")
                    elif raw and 'mil' in str(raw).lower() and (not parsed or parsed > 1000000):
                        print(f"[API] posible discrepancia raw contiene 'mil' pero parsed grande/absente: parsed={parsed} raw={raw!r} title={it.get('title')!r} url={it.get('url')}")
        except Exception:
            pass

        # El resto de la lógica de procesamiento no cambia
        final_results = []
        seen_urls = set()
        for item in all_results:
            if isinstance(item, dict):
                url = item.get("url")
                raw_price_numeric = item.get("price_numeric")
                price_numeric = raw_price_numeric
                # Asegurar que price_numeric sea numérico: intentar coerción o parseo desde price_display/price
                if not isinstance(price_numeric, (int, float)):
                    # Intentar convertir string directamente
                    try:
                        price_numeric = float(price_numeric)
                    except Exception:
                        price_numeric = None
                if price_numeric is None:
                    # Fallback: parsear desde price_display o price si existen
                    def money_to_float(s: str):
                        if not s or not isinstance(s, str):
                            return None
                        import re as _re
                        s2 = _re.sub(r"[^\d.,]", "", s)
                        if "," in s2 and "." in s2:
                            s2 = s2.replace(".", "").replace(",", ".")
                        elif "." in s2 and "," not in s2:
                            parts = s2.split(".")
                            if len(parts[-1]) == 3 and len(parts) > 1:
                                s2 = "".join(parts)
                        elif "," in s2 and "." not in s2:
                            parts = s2.split(",")
                            if len(parts[-1]) == 3 and len(parts) > 1:
                                s2 = "".join(parts)
                            else:
                                s2 = s2.replace(",", ".")
                        try:
                            return float(s2)
                        except Exception:
                            return None
                    price_numeric = money_to_float(item.get("price_display")) or money_to_float(item.get("price"))

                print(f"[API] Revisando item: url={url}, price_numeric={price_numeric}, type={type(price_numeric)} (raw={raw_price_numeric})")
                if url and url not in seen_urls and isinstance(price_numeric, (int, float)):
                    seen_urls.add(url)
                    # Incluir reviews_count_raw explícitamente en respuesta para debug/transparencia
                    item["price_numeric"] = price_numeric
                    final_results.append(item)
                else:
                    print(f"[API] Item filtrado: url={url}, precio_valido={isinstance(price_numeric, (int, float))}, url_duplicada={url in seen_urls if url else 'N/A'}")
        
        print(f"[API] Items después de filtrado: {len(final_results)} de {len(all_results)}")

        # Centralizar cálculo de 'on_sale' y 'discount_percent' aquí.
        for it in final_results:
            try:
                is_disc = it.get('is_discounted', None)
                p = it.get('price_numeric')
                pb = it.get('price_before_numeric')

                if is_disc is True:
                    # Spider explicitó que está en descuento
                    it['on_sale'] = True
                    if pb is not None and p is not None and pb > 0:
                        try:
                            it['discount_percent'] = round((pb - p) / pb * 100, 2)
                        except Exception:
                            it['discount_percent'] = None
                    else:
                        it['discount_percent'] = None
                elif is_disc is False:
                    # Spider explicitó que no está en descuento
                    it['on_sale'] = False
                    it['discount_percent'] = None
                else:
                    # Fallback: inferir por precios si el spider no envió la señal
                    if pb is not None and p is not None and pb > p * 1.01:
                        it['on_sale'] = True
                        try:
                            it['discount_percent'] = round((pb - p) / pb * 100, 2)
                        except Exception:
                            it['discount_percent'] = None
                    else:
                        it['on_sale'] = False
                        it['discount_percent'] = None
            except Exception as e:
                print(f"[API] Error calculando descuento para item {it.get('url')}: {e}")
                it['on_sale'] = False
                it['discount_percent'] = None

        final_results.sort(key=lambda x: (-x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))
        return {"status": "SUCCESS", "results": final_results, "debug_info": {"reviews_count_raw_included": True}}
    else:
        return {"status": "PENDING", "completed": f"{result_group.completed_count()}/{len(result_group)}"}