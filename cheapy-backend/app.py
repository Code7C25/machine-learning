import subprocess
import json
import threading
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import re

app = FastAPI(title="Cheapy Scraper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

# ⚠️ Usá tu ruta real a scrapy.exe (esta es la que habías pasado antes)
SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"

def clean_price(price_str: str) -> Optional[float]:
    if not isinstance(price_str, str):
        return None
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
        "-o", "-:jsonlines"  # dejamos los logs (sin --nolog)
    ]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
            encoding="latin-1",    # Windows imprime cp1252/latin-1
            errors="ignore",       # ignorar caracteres que no se puedan decodificar
            creationflags=subprocess.CREATE_NO_WINDOW
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        # Logs técnicos (truncados para no inundar la consola)
        print("\n[APP] --- STDOUT de Scrapy (técnico) ---")
        print(stdout[:1200] + ("..." if len(stdout) > 1200 else ""))
        print("[APP] --- STDERR de Scrapy (técnico) ---")
        print(stderr[:1200] + ("..." if len(stderr) > 1200 else ""))

        # Extraer sólo líneas JSON (los yield del spider)
        for line in stdout.splitlines():
            s = line.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    results_list.append(json.loads(s))
                except json.JSONDecodeError as e:
                    print(f"[APP] ⚠️ Línea JSON inválida ignorada: {e}")
    except Exception as e:
        print(f"[APP] ❌ Error ejecutando spider '{spider_name}': {e}")

@app.get("/buscar")
def buscar_producto(q: str):
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    print("\n" + "=" * 60)
    print(f"[APP] 🔎 NUEVA BÚSQUEDA: '{q}' (solo Mercado Libre)")
    print("=" * 60)

    # 1) Ejecutar spider
    raw_results: list[dict] = []
    t = threading.Thread(target=run_spider, args=("mercadolibre", q, raw_results))
    t.start()
    t.join(timeout=60.0)

    # 2) Limpieza y deduplicación
    print(f"[APP] Se encontraron {len(raw_results)} resultados en total (con posibles duplicados).")
    seen = set()
    cleaned: list[dict] = []
    for item in raw_results:
        url = item.get("url")
        price = item.get("price")
        price_num = clean_price(price)
        if url and url not in seen and price_num is not None:
            seen.add(url)
            item["price_numeric"] = price_num
            cleaned.append(item)

    print(f"[APP] {len(cleaned)} resultados ÚNICOS después de limpiar y pre-procesar.")

    # 3) Resumen simple (para vos)
    print("=" * 60)
    print("[RESUMEN SIMPLE APP]")
    print(f"- Resultados totales recibidos: {len(raw_results)}")
    print(f"- Resultados únicos válidos: {len(cleaned)}")
    print("=" * 60)

    if not cleaned:
        print("[APP] ❌ No se encontraron productos válidos para devolver.")
        print("=" * 60)
        return {"query": q, "message": "No se encontraron resultados válidos."}

    # 4) Orden final (primero más reseñas y luego precio)
    cleaned.sort(key=lambda x: (-x.get("reviews_count", 0), x["price_numeric"]))

    print(f"[APP] ✅ Se devolverán {len(cleaned)} resultados al frontend.")
    print("=" * 60)
    return {"query": q, "results": cleaned}
