import httpx
import time
import sqlite3
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from celery import group
from celery.result import GroupResult
from worker.celery_app import celery as celery_app
from config import COUNTRY_TO_SPIDERS

def calculate_similarity_score(title: str, query: str) -> int:
    """
    Calcula el puntaje de similitud entre el título del producto y la consulta del usuario.

    Utiliza un algoritmo optimizado basado en conjuntos para calcular la similitud,
    considerando el porcentaje de palabras de la consulta que aparecen en el título.

    Args:
        title: Título del producto a comparar
        query: Consulta del usuario para búsqueda

    Returns:
        Puntaje de similitud (0-100, donde 100 es coincidencia perfecta)

    Example:
        >>> calculate_similarity_score("iPhone 15 Pro Max", "iPhone Pro")
        67
    """
    if not title or not query:
        return 0

    # Normalizar texto: convertir a minúsculas y dividir en palabras
    title_words = set(title.lower().split())
    query_words = set(query.lower().split())

    # Calcular intersección de palabras (palabras comunes)
    common_words = title_words.intersection(query_words)

    # Puntaje basado en porcentaje de palabras coincidentes
    if not query_words:
        return 0

    similarity = (len(common_words) / len(query_words)) * 100
    return int(similarity)

# Inicializar aplicación FastAPI con middleware CORS para solicitudes de origen cruzado
app = FastAPI(title="Cheapy Scraper API - Async")
logger = logging.getLogger("cheapy.api")
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s %(name)s: %(message)s")
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DB_FILE = BASE_DIR / "cache.db"
CACHE_DURATION_SECONDS = 86400

def setup_cache_database():
    """
    Configura la base de datos SQLite para almacenar en caché las asignaciones IP-país.
    Crea la tabla si no existe para almacenar datos de geolocalización con marcas de tiempo.
    """
    conn = sqlite3.connect(CACHE_DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS ip_cache (ip TEXT PRIMARY KEY, country TEXT, timestamp REAL)")
    conn.commit()
    conn.close()

setup_cache_database()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

async def get_country_from_ip(ip: str) -> str:
    """
    Obtiene el código de país desde una dirección IP utilizando una API externa con caché local.
    Retrocede a 'AR' si la API falla o el caché está obsoleto.
    Almacena en caché los resultados por 24 horas para reducir las llamadas a la API.
    """
    default_country = "AR"
    conn = sqlite3.connect(CACHE_DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT country, timestamp FROM ip_cache WHERE ip = ?", (ip,))
        result = cursor.fetchone()
        if result and (time.time() - result[1] < CACHE_DURATION_SECONDS):
            return result[0]
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("https://ipapi.co/json/")
            response.raise_for_status()
            data = response.json()
        country_code = data.get("country_code")
        if country_code:
            country_code = country_code.upper()
            cursor.execute("INSERT OR REPLACE INTO ip_cache VALUES (?, ?, ?)", (ip, country_code, time.time()))
            conn.commit()
            return country_code
        return default_country
    except Exception:
        return default_country
    finally:
        conn.close()

@app.get("/buscar")
async def buscar_producto(q: str, request: Request, country: str = None):
    """
    Inicia la búsqueda asíncrona de productos en múltiples spiders de comercio electrónico.
    Prioriza el país proporcionado por el cliente, retrocede a geolocalización por IP.
    Devuelve el ID de tarea para consultar resultados.
    """
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    country_code = ""
    if country:
        country_code = country.upper()
        logger.info(f"País recibido del frontend: %s", country_code)
    else:
        logger.info("No se recibió país; usando geolocalización por IP")
        client_ip = request.client.host
        country_code = await get_country_from_ip(client_ip)

    # --- MODO DE PRUEBA (OPCIONAL) ---
    # Para forzar un país durante el desarrollo, puedes sobreescribir la variable aquí.
    # country_code = "US"

    spiders_to_run = COUNTRY_TO_SPIDERS.get(country_code, [])
    if not spiders_to_run:
        return {"task_id": None, "error": f"No hay tiendas para tu región ({country_code})."}

    logger.info("Tarea recibida q=%r country=%s spiders=%s", q, country_code, spiders_to_run)

    task_signatures = [
        celery_app.signature('run_scrapy_spider_task', kwargs={'spider_name': name, 'query': q, 'country': country_code})
        for name in spiders_to_run
    ]
    result_group = group(task_signatures).apply_async()
    result_group.save()
    celery_app.backend.set(f"query:{result_group.id}", q)
    return {"task_id": result_group.id, "query": q}

@app.get("/resultados/{task_id}")
def get_status(task_id: str):
    """
    Consulta los resultados de búsqueda desde el grupo de tareas de Celery.
    Procesa y filtra resultados: deduplica por URL, normaliza precios,
    calcula descuentos y ordena por similitud, reseñas y precio.
    """
    result_group = GroupResult.restore(task_id, app=celery_app)
    if not result_group:
        return {"status": "FAILURE", "error": "ID de tarea no encontrado."}
    if result_group.failed():
        return {"status": "FAILURE", "error": "Al menos una tarea falló."}

    if result_group.ready():
        results_from_worker_group = result_group.get(propagate=False)
        logger.info("Resultados recuperados de Redis: %d tareas respondieron", len(results_from_worker_group))
        logger.debug("Contenido bruto de resultados_from_worker_group: %s", results_from_worker_group)

        all_results = [item for sublist in results_from_worker_group if sublist for item in sublist]
        logger.info("Total de items después de aplanar: %d", len(all_results))

        try:
            for it in all_results:
                if isinstance(it, dict):
                    raw = it.get('reviews_count_raw')
                    parsed = it.get('reviews_count')
                    if parsed and parsed > 1000000:
                        logger.warning("reviews_count grande detectado: parsed=%s raw=%r title=%r url=%s", parsed, raw, it.get('title'), it.get('url'))
                    elif raw and 'mil' in str(raw).lower() and (not parsed or parsed > 1000000):
                        logger.warning("posible discrepancia reviews: parsed=%s raw=%r title=%r url=%s", parsed, raw, it.get('title'), it.get('url'))
        except Exception:
            pass

        final_results = []
        seen_urls = set()
        for item in all_results:
            if isinstance(item, dict):
                url = item.get("url")
                raw_price_numeric = item.get("price_numeric")
                price_numeric = raw_price_numeric
                if not isinstance(price_numeric, (int, float)):
                    try:
                        price_numeric = float(price_numeric)
                    except Exception:
                        price_numeric = None
                if price_numeric is None:
                    def money_to_float(s: str):
                        """
                        Parsea cadenas monetarias en float, manejando formatos europeos y estadounidenses.
                        Elimina caracteres no numéricos y ajusta separadores decimales.
                        """
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

                logger.debug("Revisando item url=%s price_numeric=%s type=%s (raw=%s)", url, price_numeric, type(price_numeric), raw_price_numeric)
                if url and url not in seen_urls and isinstance(price_numeric, (int, float)):
                    seen_urls.add(url)
                    item["price_numeric"] = price_numeric
                    final_results.append(item)
                else:
                    logger.debug("Item filtrado url=%s precio_valido=%s url_duplicada=%s", url, isinstance(price_numeric, (int, float)), (url in seen_urls if url else 'N/A'))

        logger.info("Items después de filtrado: %d de %d", len(final_results), len(all_results))

        for it in final_results:
            try:
                is_disc = it.get('is_discounted', None)
                p = it.get('price_numeric')
                pb = it.get('price_before_numeric')

                if is_disc is True:
                    it['on_sale'] = True
                    if pb is not None and p is not None and pb > 0:
                        try:
                            it['discount_percent'] = round((pb - p) / pb * 100, 2)
                        except Exception:
                            it['discount_percent'] = None
                    else:
                        it['discount_percent'] = None
                elif is_disc is False:
                    it['on_sale'] = False
                    it['discount_percent'] = None
                else:
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
                logger.exception("Error calculando descuento para item %s", it.get('url'))
                it['on_sale'] = False
                it['discount_percent'] = None

        query = celery_app.backend.get(f"query:{task_id}")
        if query:
            query = query.decode('utf-8') if isinstance(query, bytes) else query
        else:
            query = ""

        for item in final_results:
            item['similarity_score'] = calculate_similarity_score(item.get('title', ''), query)

        final_results.sort(key=lambda x: (-x.get("similarity_score", 0), -x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))
        return {"status": "SUCCESS", "results": final_results, "debug_info": {"reviews_count_raw_included": True}}
    else:
        return {"status": "PENDING", "completed": f"{result_group.completed_count()}/{len(result_group)}"}