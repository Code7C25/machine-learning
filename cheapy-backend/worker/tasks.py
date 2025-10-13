# cheapy-backend/worker/tasks.py

import subprocess
import json
import sys
from pathlib import Path
from .celery_app import celery

SCRAPY_PROJECT_PATH = str(Path(__file__).resolve().parent.parent)

# --- ¡CAMBIO IMPORTANTE! ---
# Le damos un nombre explícito a la tarea. Este será su identificador único.
@celery.task(name='run_scrapy_spider_task')
def run_scrapy_spider(query: str, country: str):
    command = [
        sys.executable, "-m", "scrapy", "crawl", "mercadolibre",
        "-a", f"query={query}",
        "-a", f"country={country}",
        "-o", "-:jsonlines"
    ]
    
    try:
        # ... (el resto de la función es idéntico a la que ya tienes)
        result = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding="utf-8", errors="ignore", cwd=SCRAPY_PROJECT_PATH
        )
        raw_results = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        # ... (procesamiento y ordenamiento)
        final_results = []
        seen_urls = set()
        for item in raw_results:
            url = item.get("url")
            if url and url not in seen_urls and isinstance(item.get("price_numeric"), (int, float)):
                seen_urls.add(url)
                final_results.append(item)
        final_results.sort(key=lambda x: (-x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))
        return final_results
    except Exception as e:
        print(f"ERROR en Worker: {e}")
        # En caso de error, es mejor que la tarea falle para que podamos verlo en el status
        raise e