# cheapy-backend/cheapy_scraper/pipelines.py

import re
from itemadapter import ItemAdapter

class DataCleaningPipeline:
    def process_item(self, item, spider):
        adapter = ItemAdapter(item)

        # --- 1. Limpieza de Precio y Moneda (VERSIÓN MEJORADA) ---
        price_str = adapter.get('price')
        if price_str:
            # Eliminar símbolos de moneda, espacios en blanco y cualquier cosa que no sea un número, punto o coma.
            cleaned_str = re.sub(r'[^\d,.]', '', price_str)
            
            # Lógica para manejar formatos de LATAM (ej: 1.234,56)
            # 1. Quitar los puntos (separadores de miles)
            cleaned_str = cleaned_str.replace('.', '')
            # 2. Reemplazar la coma (separador decimal) por un punto
            cleaned_str = cleaned_str.replace(',', '.')

            try:
                # Ahora la conversión a float será precisa
                adapter['price_numeric'] = float(cleaned_str)
                # Por ahora, asumimos ARS para Mercado Libre Argentina
                # En el futuro, podríamos detectar la moneda desde la página
                adapter['currency'] = 'ARS' 
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
        
        return item