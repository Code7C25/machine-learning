# cheapy-backend/cheapy_scraper/pipelines.py

import re
from itemadapter import ItemAdapter

class DataCleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

    # --- 1. Limpieza de Precio y Moneda ---
        price_str = adapter.get('price')
        # Obtenemos la moneda que el spider nos pasó
        currency_code = adapter.get('currency_code')
        
        if price_str:
            cleaned_str = re.sub(r'[^\d,.]', '', price_str)
            cleaned_str = cleaned_str.replace('.', '')
            cleaned_str = cleaned_str.replace(',', '.')

            try:
                adapter['price_numeric'] = float(cleaned_str)
                # Asignamos la moneda correcta
                adapter['currency'] = currency_code
            except (ValueError, TypeError):
                adapter['price_numeric'] = None
                adapter['currency'] = None
        else:
            adapter['price_numeric'] = None
            adapter['currency'] = None
        # --- 2. Limpieza de Calificación (Rating) ---
        # (Esta lógica ya estaba bien, pero la incluimos por completitud)
        rating_str = adapter.get('rating_str')
        if rating_str:
            try:
                adapter['rating'] = float(rating_str.replace(',', '.'))
            except (ValueError, TypeError):
                adapter['rating'] = 0.0
        else:
            adapter['rating'] = 0.0

        # --- 3. Limpieza de Cantidad de Reseñas ---
        # (Esta lógica ya estaba bien)
        reviews_str = adapter.get('reviews_count_str')
        if reviews_str:
            numbers = re.findall(r'\d+', reviews_str)
            if numbers:
                adapter['reviews_count'] = int("".join(numbers))
            else:
                adapter['reviews_count'] = 0
        else:
            adapter['reviews_count'] = 0
        
        # Eliminar los campos "crudos" que ya no necesitamos
        adapter.pop('price', None)
        adapter.pop('rating_str', None)
        adapter.pop('reviews_count_str', None)
        adapter.pop('currency_code', None)
        
        return item