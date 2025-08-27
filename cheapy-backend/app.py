import subprocess
import json
import threading
from fastapi import FastAPI, HTTPException
from typing import Optional
import re
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Cheapy Scraper API")

# --- Configuración de CORS (ya la tenías, la mantenemos) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"

# --- NUEVA FUNCIÓN AUXILIAR PARA LIMPIAR PRECIOS ---
def clean_price(price_str: str) -> Optional[float]:
    if not isinstance(price_str, str): return None
    try:
        # Lógica de limpieza mejorada
        cleaned_str = re.sub(r'[^\d,.]', '', price_str)
        if ',' in cleaned_str and '.' in cleaned_str:
             cleaned_str = cleaned_str.replace('.', '').replace(',', '.')
        else:
             cleaned_str = cleaned_str.replace(',', '.')
        return float(cleaned_str)
    except (ValueError, TypeError):
        print(f"ADVERTENCIA: No se pudo convertir el precio '{price_str}' a número.")
        return None

# La función run_spider se queda exactamente igual
def run_spider(spider_name: str, query: str, results_list: list):
    command = [
        SCRAPY_PATH, "crawl", spider_name,
        "-a", f"query={query}",
        "-o", "-:jsonlines",
        "--nolog"
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


# --- ENDPOINT MODIFICADO PARA ACEPTAR Y APLICAR FILTROS ---
@app.get("/buscar")
def buscar_producto(
    q: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_reliability: Optional[int] = None
):
    print("\n" + "="*50)
    print(f"NUEVA BÚSQUEDA: '{q}'")
    print(f"Filtros recibidos: min_price={min_price}, max_price={max_price}, min_reliability={min_reliability}")
    print("="*50)
    
    all_results_with_duplicates = []
    
    ebay_thread = threading.Thread(target=run_spider, args=("ebay", q, all_results_with_duplicates))
    ml_thread = threading.Thread(target=run_spider, args=("mercadolibre", q, all_results_with_duplicates))
    
    ebay_thread.start()
    ml_thread.start()
    
    ebay_thread.join(timeout=30.0)
    ml_thread.join(timeout=30.0)

    # --- ¡NUEVO PASO DE LIMPIEZA Y DEDUPLICACIÓN! ---
    print(f"\nSe encontraron {len(all_results_with_duplicates)} resultados en total (con posibles duplicados).")
    
    seen_urls = set()
    all_results = []
    for item in all_results_with_duplicates:
        url = item.get('url')
        if url and url not in seen_urls:
            seen_urls.add(url)
            all_results.append(item)
    
    print(f"Se encontraron {len(all_results)} resultados ÚNICOS antes de filtrar.")
    print("--- INICIANDO PROCESO DE FILTRADO ---")
    
    # El resto de la lógica de filtrado ahora usa la lista limpia `all_results`
    filtered_results = []
    for i, item in enumerate(all_results):
        print(f"\n[Item {i+1}] Procesando: {item.get('title', 'SIN TITULO')}")
        
        item_price_str = item.get('price')
        item_price_num = clean_price(item_price_str)
        item_reliability = item.get('reliability_score', 0)
        
        print(f"  - Precio (str): '{item_price_str}' -> Precio (num): {item_price_num}")
        print(f"  - Confiabilidad: {item_reliability}")

        passes_min_price = min_price is None or (item_price_num is not None and item_price_num >= min_price)
        passes_max_price = max_price is None or (item_price_num is not None and item_price_num <= max_price)
        passes_reliability = min_reliability is None or item_reliability >= min_reliability
        
        print(f"  - ¿Pasa min_price ({min_price})? -> {passes_min_price}")
        print(f"  - ¿Pasa max_price ({max_price})? -> {passes_max_price}")
        print(f"  - ¿Pasa min_reliability ({min_reliability})? -> {passes_reliability}")
        
        if passes_min_price and passes_max_price and passes_reliability:
            filtered_results.append(item)
            print("  --> RESULTADO: INCLUIDO")
        else:
            print("  --> RESULTADO: EXCLUIDO")

    print("\n--- FIN DEL PROCESO DE FILTRADO ---")
    print(f"Se incluyeron {len(filtered_results)} resultados después de filtrar.")
    print("="*50 + "\n")

    if not filtered_results:
        return {"query": q, "message": "No se encontraron resultados que coincidan con tus filtros."}
        
    return {"query": q, "results": filtered_results}