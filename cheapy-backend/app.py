import subprocess
import json
import threading
from fastapi import FastAPI, HTTPException
import sys
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cheapy Scraper API")

origins = [
    "*",  # Permitir todas las fuentes (no recomendado para producción)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Permite todos los métodos (GET, POST, etc.)
    allow_headers=["*"], # Permite todas las cabeceras
)

# La ruta completa y explícita a tu ejecutable de scrapy.exe.
SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"


def run_spider(spider_name: str, query: str, results_list: list):
    """
    Ejecuta un spider de Scrapy como un subproceso y añade sus resultados a una lista.
    """
    # --- ¡ESTA ES LA LÍNEA CORREGIDA Y DEFINITIVA! ---
    # Unimos la salida y el formato en un solo argumento "-o -:jsonlines"
    command = [
        SCRAPY_PATH,
        "crawl",
        spider_name,
        "-a", f"query={query}",
        "-o", "-:jsonlines", # SALIDA: consola (-), FORMATO: jsonlines
        "--nolog"
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        for line in result.stdout.strip().split('\n'):
            if line:
                results_list.append(json.loads(line))
                
    except subprocess.CalledProcessError as e:
        print(f"Error ejecutando el spider '{spider_name}': {e.stderr}")
    except FileNotFoundError:
        print(f"ERROR: No se pudo encontrar 'scrapy.exe' en la ruta: {SCRAPY_PATH}")
    except Exception as e:
        print(f"Error inesperado con el spider '{spider_name}': {e}")


@app.get("/buscar")
def buscar_producto(q: str):
    """
    Inicia los spiders en hilos separados, cada uno ejecutando un subproceso de Scrapy.
    """
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    results = []
    
    ebay_thread = threading.Thread(target=run_spider, args=("ebay", q, results))
    ml_thread = threading.Thread(target=run_spider, args=("mercadolibre", q, results))
    
    ebay_thread.start()
    ml_thread.start()
    
    ebay_thread.join(timeout=30.0)
    ml_thread.join(timeout=30.0)

    if not results:
        return {"query": q, "message": "No se encontraron resultados."}
        
    return {"query": q, "results": results}