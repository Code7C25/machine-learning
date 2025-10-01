# cheapy-backend/app.py

import subprocess
import json
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
# El import 're' y la función 'clean_price' ya no son necesarios aquí.

app = FastAPI(title="Cheapy Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"

def run_spider(spider_name: str, query: str, results_list: list):
    command = [
        SCRAPY_PATH, "crawl", spider_name,
        "-a", f"query={query}",
        "-o", "-:jsonlines"
    ]
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=True,
            encoding="latin-1", errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        for line in result.stdout.splitlines():
            s = line.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    # Los datos que llegan aquí ya están limpios gracias a la pipeline
                    results_list.append(json.loads(s))
                except json.JSONDecodeError as e:
                    print(f"[APP] ⚠️ Línea JSON inválida ignorada: {e}")
    except Exception as e:
        print(f"[APP] ❌ Error ejecutando spider '{spider_name}': {e}")


@app.get("/buscar")
def buscar_producto(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    print(f"\n[APP] 🔎 NUEVA BÚSQUEDA: '{q}' (solo Mercado Libre)")

    # 1. Ejecutar spider y obtener resultados YA LIMPIOS
    raw_results: list[dict] = []
    t = threading.Thread(target=run_spider, args=("mercadolibre", q, raw_results))
    t.start()
    t.join(timeout=60.0)

    # 2. Deduplicación (la única limpieza que queda aquí)
    print(f"[APP] Se encontraron {len(raw_results)} resultados limpios (con posibles duplicados).")
    seen_urls = set()
    final_results: list[dict] = []
    for item in raw_results:
        url = item.get("url")
        # Ahora solo verificamos que la URL exista y no esté duplicada
        if url and url not in seen_urls:
            seen_urls.add(url)
            final_results.append(item)

    print(f"[APP] {len(final_results)} resultados ÚNICOS después de deduplicar.")
    
    if not final_results:
        return {"query": q, "message": "No se encontraron resultados válidos."}

    # 3. Orden final (usando los nuevos campos numéricos)
    final_results.sort(key=lambda x: (-x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))

    print(f"[APP] ✅ Se devolverán {len(final_results)} resultados al frontend.")
    return {"query": q, "results": final_results}