import subprocess
import json
import sys
from pathlib import Path
from .celery_app import celery 

SCRAPY_PROJECT_PATH = str(Path(__file__).resolve().parent.parent)

@celery.task(name='run_scrapy_spider_task')
def run_scrapy_spider(store_name: str, query: str, country: str):
    """
    Ejecuta el GenericSpider de Scrapy para una tienda específica.
    El GenericSpider lee su configuración de un archivo JSON basado en store_name.
    """
    print(f"[WORKER] Iniciando tarea para tienda: '{store_name}', Query: '{query}', País: '{country}'")
    
    command = [
        sys.executable, "-m", "scrapy", "crawl", "generic_spider", 
        "-a", f"store_name={store_name}",                         
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
        
        print(f"[WORKER] Tarea para tienda '{store_name}' finalizada con {len(raw_results)} resultados.")
        return raw_results
    
    except subprocess.CalledProcessError as e:
        print(f"ERROR en Worker ejecutando GenericSpider para '{store_name}':") # <-- ¡CAMBIO AQUÍ!
        print(f"  Comando: {e.cmd}")
        print(f"  Exit Code: {e.returncode}")
        print(f"  Stderr: {e.stderr}")
        raise e
    
    except Exception as e:
        print(f"ERROR inesperado en Worker ejecutando GenericSpider para '{store_name}': {e}") # <-- ¡CAMBIO AQUÍ!
        raise e