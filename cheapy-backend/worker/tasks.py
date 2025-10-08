# worker/tasks.py
import subprocess
import json
import sys
from pathlib import Path
from .celery_app import celery

# Definimos la ruta base del proyecto Scrapy
SCRAPY_PROJECT_PATH = str(Path(__file__).resolve().parent.parent / "cheapy_scraper")

@celery.task
def run_scrapy_spider(query: str, country: str):
    """
    Una tarea de Celery que ejecuta el spider de Scrapy en un subproceso.
    """
    command = [
        sys.executable, "-m", "scrapy", "crawl", "mercadolibre",
        "-a", f"query={query}",
        "-a", f"country={country}",
        "-o", "-:jsonlines"
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding="utf-8",
            errors="ignore",
            cwd=SCRAPY_PROJECT_PATH
        )
        
        raw_results = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]

        # Procesamiento y ordenamiento de resultados
        final_results = []
        seen_urls = set()
        for item in raw_results:
            url = item.get("url")
            if url and url not in seen_urls and isinstance(item.get("price_numeric"), (int, float)):
                seen_urls.add(url)
                final_results.append(item)
        
        final_results.sort(key=lambda x: (-x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))
        
        return final_results # Celery guardará este retorno en el backend de resultados (Redis)

    except subprocess.CalledProcessError as e:
        # Si el scraper falla, podemos devolver el error para que el frontend lo sepa
        print(f"ERROR en Subproceso Scrapy: {e.stderr}")
        return {"error": "El scraper falló", "details": e.stderr}
    except Exception as e:
        print(f"ERROR Inesperado: {e}")
        return {"error": "Ocurrió un error inesperado en el worker", "details": str(e)}