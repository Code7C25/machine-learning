from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import sqlite3
import os

app = Flask(__name__)
CORS(app)

DB_PATH = os.path.join(os.path.dirname(__file__), 'productos.db')

# Create DB if not exists
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS resultados (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consulta TEXT,
            titulo TEXT,
            precio_num REAL,
            precio_raw TEXT,
            dominio TEXT,
            link TEXT,
            clasificacion TEXT,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# Simple MercadoLibre scraper (very basic selectors)
def scrape_mercadolibre(query):
    url = f"https://listado.mercadolibre.com.ar/{query.replace(' ', '-') }"
    res = requests.get(url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
    res.raise_for_status()
    soup = BeautifulSoup(res.text, 'html.parser')
    items = []
    cards = soup.select('.ui-search-layout__item')
    for c in cards[:8]:
        title = c.select_one('.ui-search-item__title')
        price = c.select_one('.andes-money-amount__fraction')
        img = c.select_one('.ui-search-result-image__element')
        link = c.select_one('a.ui-search-link')
        if title and price and link:
            title_text = title.get_text(strip=True)
            price_raw = price.get_text(strip=True)
            try:
                price_num = float(price_raw.replace('.', '').replace(',', '.'))
            except:
                price_num = None
            img_url = img.get('data-src') or img.get('src') if img else None
            items.append({
                'titulo': title_text,
                'precio_raw': price_raw,
                'precio_num': price_num,
                'dominio': 'mercadolibre.com.ar',
                'link': link.get('href'),
                'imagen': img_url
            })
    return items

@app.route('/buscar')
def buscar():
    q = request.args.get('q')
    if not q:
        return jsonify({'error': 'missing query'}), 400

    # call scrapers
    results = []
    try:
        ml = scrape_mercadolibre(q)
        results.extend(ml)
    except Exception as e:
        print('ML error', e)

    # Store into sqlite
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for r in results:
        cur.execute('''INSERT INTO resultados (consulta, titulo, precio_num, precio_raw, dominio, link, clasificacion)
                       VALUES (?, ?, ?, ?, ?, ?, ?)''', (q, r['titulo'], r['precio_num'], r['precio_raw'], r['dominio'], r['link'], None))
    conn.commit()
    conn.close()

    # compute cheap, secure, official (placeholder rules)
    destacado = {'barato': None, 'barata_seguridad': None, 'oficial': None}
    if results:
        sorted_by_price = sorted([r for r in results if r['precio_num'] is not None], key=lambda x: x['precio_num'])
        if sorted_by_price:
            destacado['barato'] = sorted_by_price[0]
            destacado['barata_seguridad'] = sorted_by_price[0]
            destacado['oficial'] = sorted_by_price[0]

    return jsonify({'items': results, 'destacados': destacado})

if __name__ == '__main__':
    app.run(port=3000, debug=True)
