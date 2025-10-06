import subprocess
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# --- 1. Configuración de la Aplicación y Constantes ---
app = FastAPI(title="Cheapy Scraper API")
BASE_DIR = Path(__file__).resolve().parent
SCRAPY_PATH = r"C:\Users\Usuario\AppData\Local\Programs\Python\Python313\Scripts\scrapy.exe"

# --- 2. Middleware de CORS ---
# Permite que la extensión se comunique con el servidor.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Para producción, se recomienda restringir esto al ID de tu extensión.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 3. Endpoint Principal de la API ---
@app.get("/buscar")
def buscar_producto(q: str, country: str = "AR"):
    """
    Endpoint principal que recibe una búsqueda y un código de país,
    ejecuta el scraper de Scrapy y devuelve los resultados procesados.
    """
    if not q:
        raise HTTPException(status_code=400, detail="El parámetro 'q' es requerido.")

    # El código de país ahora es proporcionado por el frontend.
    # Usamos 'AR' como un valor por defecto seguro si no se envía.
    country_code = country.upper()
    
    print(f"\n[ENDPOINT] 🔎 Búsqueda: '{q}', País: {country_code} (recibido del frontend)")
    
    # Lista para almacenar los resultados del scraper
    raw_results = []
    
    # Comando para ejecutar Scrapy como un subproceso
    command = [
        SCRAPY_PATH, "crawl", "mercadolibre",
        "-a", f"query={q}",
        "-a", f"country={country_code}",
        "-o", "-:jsonlines"
    ]
    
    try:
        # Ejecuta el comando y captura la salida
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,  # Lanza una excepción si el scraper falla
            encoding="latin-1",
            errors="ignore",
            creationflags=subprocess.CREATE_NO_WINDOW  # Evita que se abra una ventana de consola en Windows
        )
        # Procesa cada línea de la salida como un objeto JSON
        for line in result.stdout.splitlines():
            clean_line = line.strip()
            if clean_line.startswith("{") and clean_line.endswith("}"):
                try:
                    raw_results.append(json.loads(clean_line))
                except json.JSONDecodeError:
                    print(f"[ENDPOINT] ⚠️ Línea JSON inválida ignorada: {clean_line}")
    except subprocess.CalledProcessError as e:
        # Captura errores del propio scraper
        print(f"[ENDPOINT] ❌ Error en el subproceso de Scrapy: {e.stderr}")
    except Exception as e:
        print(f"[ENDPOINT] ❌ Error inesperado ejecutando Scrapy: {e}")

    # --- Procesamiento de los resultados ---
    print(f"[ENDPOINT] Se encontraron {len(raw_results)} resultados crudos.")
    
    final_results = []
    seen_urls = set()
    for item in raw_results:
        url = item.get("url")
        # Filtra items duplicados o sin información de precio válida
        if url and url not in seen_urls and isinstance(item.get("price_numeric"), (int, float)):
            seen_urls.add(url)
            final_results.append(item)
    
    print(f"[ENDPOINT] {len(final_results)} resultados únicos y válidos.")
    
    if not final_results:
        return {"query": q, "message": "No se encontraron resultados válidos."}

    # Ordena los resultados por número de reseñas (descendente) y luego por precio (ascendente)
    final_results.sort(key=lambda x: (-x.get("reviews_count", 0), x.get("price_numeric", float('inf'))))
    
    print(f"[ENDPOINT] ✅ Devolviendo {len(final_results)} resultados al frontend.")
    return {"query": q, "results": final_results}