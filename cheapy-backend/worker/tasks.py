import subprocess
import json
import sys
from pathlib import Path
from .celery_app import celery

SCRAPY_PROJECT_PATH = str(Path(__file__).resolve().parent.parent)

@celery.task(name='run_scrapy_spider_task')
def run_scrapy_spider(spider_name: str, query: str, country: str):
    print(f"[WORKER] Iniciando tarea para spider: '{spider_name}', Query: '{query}', País: '{country}'")
    command = [
        sys.executable, "-m", "scrapy", "crawl", spider_name,
        "-a", f"query={query}", "-a", f"country={country}",
        "-o", "-:jsonlines"
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding="utf-8", errors="ignore", cwd=SCRAPY_PROJECT_PATH
        )
        raw_results = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        print(f"[WORKER] Tarea '{spider_name}' finalizada con {len(raw_results)} resultados.")
        return raw_results
    except Exception as e:
        print(f"ERROR en Worker ejecutando '{spider_name}': {e}")
        raise e