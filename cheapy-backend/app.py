import subprocess
import json
from fastapi import FastAPI, HTTPException
from typing import Optional
import re

app = FastAPI(title="Cheapy Scraper API - Mercado Libre Only")

# La ruta completa y explícita a tu ejecutable de scrapy.exe.
SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"


def clean_price(price_str: str) -> Optional[float]:
    """Convierte un string de precio a un número flotante."""
    if not isinstance(price_str, str):
        return None
    try:
        cleaned_str = re.sub(r'[^\d,]', '', price_str).replace(',', '.')
        return float(cleaned_str)
    except (ValueError, TypeError):
        print(f"ADVERTENCIA: No se pudo convertir el precio '{price_str}' a número.")
        return None


@app.get("/buscar")
def buscar_producto(
    q: str,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_reliability: Optional[int] = None
):
    """
    Ejecuta el spider de Mercado Libre y filtra los resultados.
    """
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    print("\n" + "="*50)
    print(f"NUEVA BÚSQUEDA (SOLO ML): '{q}'")
    print(f"Filtros recibidos: min_price={min_price}, max_price={max_price}, min_reliability={min_reliability}")
    print("="*50)

    # --- Ejecutamos SOLAMENTE el spider de Mercado Libre ---
    command = [
        SCRAPY_PATH, "crawl", "mercadolibre",
        "-a", f"query={q}",
        "-o", "-:jsonlines",
        "--nolog"
    ]
    
    all_results = []
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in result.stdout.strip().split('\n'):
            if line:
                all_results.append(json.loads(line))
    except Exception as e:
        print(f"Error crítico al ejecutar el subproceso de Scrapy: {e}")
        # Devolvemos un error claro si Scrapy falla
        raise HTTPException(status_code=500, detail="El proceso de scraping falló.")
    
    print(f"\nSe encontraron {len(all_results)} resultados de ML antes de filtrar.")
    print("--- INICIANDO PROCESO DE FILTRADO ---")

    # --- Lógica de Filtrado (la misma que teníamos, con logging) ---
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