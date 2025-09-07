import subprocess
import json
import threading
from fastapi import FastAPI, HTTPException
from typing import Optional
import re
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cheapy Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"

def clean_price(price_str: str) -> Optional[float]:
    if not isinstance(price_str, str): return None
    try:
        cleaned_str = re.sub(r'[^\d,.]', '', price_str)
        if ',' in cleaned_str and '.' in cleaned_str:
             cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
        else:
             cleaned_str = cleaned_str.replace(',', '.')
        return float(cleaned_str)
    except (ValueError, TypeError):
        return None

def run_spider(spider_name: str, query: str, results_list: list):
    command = [
        SCRAPY_PATH, "crawl", spider_name,
        "-a", f"query={query}",
        "-o", "-:jsonlines", "--nolog"
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in result.stdout.strip().split('\n'):
            if line:
                results_list.append(json.loads(line))
    except Exception as e:
        print(f"Error con el spider '{spider_name}': {e}")

@app.get("/buscar")
def buscar_producto(q: str):
    """
    Ejecuta el spider de Mercado Libre, devuelve la lista completa de resultados,
    y muestra logs detallados en la consola.
    """
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    # --- LOGGING RESTAURADO ---
    print("\n" + "="*50)
    print(f"NUEVA BÚSqueda: '{q}' (solo Mercado Libre)")
    print("="*50)
    
    # 1. Recolectar datos
    all_results_with_duplicates = []
    ml_thread = threading.Thread(target=run_spider, args=("mercadolibre", q, all_results_with_duplicates))
    ml_thread.start()
    ml_thread.join(timeout=45.0)
    
    # --- LOGGING RESTAURADO ---
    print(f"\nSe encontraron {len(all_results_with_duplicates)} resultados en total (con posibles duplicados).")

    # 2. Limpiar y pre-procesar
    seen_urls = set()
    processed_results = []
    for item in all_results_with_duplicates:
        url = item.get('url')
        price_num = clean_price(item.get('price'))
        
        if url and url not in seen_urls and price_num is not None:
            seen_urls.add(url)
            item['price_numeric'] = price_num
            processed_results.append(item)

    # --- LOGGING RESTAURADO ---
    print(f"Se encontraron {len(processed_results)} resultados ÚNICOS después de limpiar y pre-procesar.")
    
    if not processed_results:
        print("No se encontraron productos válidos para devolver.")
        print("="*50 + "\n")
        return {"query": q, "message": "No se encontraron resultados válidos."}

    # 3. Ordenar la lista
    processed_results.sort(key=lambda x: (-x.get('reviews_count', 0), x['price_numeric']))

    # --- LOGGING RESTAURADO ---
    print(f"Se devolverán {len(processed_results)} resultados al frontend.")
    print("="*50 + "\n")
    
    return {"query": q, "results": processed_results}