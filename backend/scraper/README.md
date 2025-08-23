Scraper Scrapy — instrucciones de uso

Requisitos:
- Python 3.8+ (recomendado 3.11). Scrapy puede no ser compatible con versiones muy nuevas (3.13+).

Instalación (desde la raíz del repo):

"C:\\Users\\Usuario\\AppData\\Local\\Programs\\Python\\Python313\\python.exe" -m venv backend\.venv
backend\.venv\Scripts\activate
pip install -r backend\scrapy_requirements.txt

Ejecutar spider de Mercado Libre:

cd backend\scraper
..\..\.venv\Scripts\python -m scrapy crawl mercadolibre -a query="smart tv" -o resultados.json

Esto almacenará los resultados en `productos.db` en la carpeta `backend` (vía SQLitePipeline) y además volcará `resultados.json` si usas `-o`.

Notas:
- Si la instalación de `scrapy` falla por la versión de Python, crea un entorno con Python 3.11 y repite los pasos.
- Ajusta selectores en `scraper/scraper/spiders/mercadolibre.py` si Mercado Libre cambia su HTML.
