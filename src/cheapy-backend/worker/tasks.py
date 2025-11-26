import subprocess
import json
import sys
from pathlib import Path
from .celery_app import celery

SCRAPY_PROJECT_PATH = str(Path(__file__).resolve().parent.parent)

@celery.task(
    name='run_scrapy_spider_task',
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 2}
)
def run_scrapy_spider(spider_name: str, query: str, country: str):
    """
    Ejecuta un spider de Scrapy mediante subprocess y devuelve los resultados JSON parseados.
    Configurado con reintentos automáticos en caso de fallo.
    """
    print(f"[WORKER] Iniciating task for spider: '{spider_name}', Query: '{query}', Country: '{country}'")
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
        print(f"[WORKER] Task '{spider_name}' completed with {len(raw_results)} results.")
        return raw_results
    except Exception as e:
        print(f"ERROR in Worker executing '{spider_name}': {e}")
        raise e