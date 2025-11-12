# cheapy-backend/cheapy_scraper/utils/config_loader.py

import json
import os
from pathlib import Path

SCRAPY_ROOT = Path(__file__).resolve().parent.parent
STORE_CONFIGS_DIR = SCRAPY_ROOT.joinpath('spiders', 'store_configs')

def load_store_config(store_name: str) -> dict:
    """
    Carga la configuración JSON para una tienda específica.
    Retorna un diccionario con la configuración o None si no se encuentra.
    """
    config_path = STORE_CONFIGS_DIR.joinpath(f"{store_name}.json")
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: No se pudo parsear el JSON de la configuración '{store_name}.json': {e}")
            return None
    print(f"ADVERTENCIA: Configuración '{store_name}.json' no encontrada en {config_path}")
    return None

try:
    AVAILABLE_STORES = [
        os.path.splitext(f)[0] 
        for f in os.listdir(STORE_CONFIGS_DIR) 
        if f.endswith('.json')
    ]
except FileNotFoundError:
    print(f"ADVERTENCIA: El directorio de configuraciones de tiendas no se encontró: {STORE_CONFIGS_DIR}")
    AVAILABLE_STORES = []