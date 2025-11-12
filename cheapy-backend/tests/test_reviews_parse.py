# Test rápido para validar el parseo de reviews_count_str en DataCleaningPipeline
import sys
from pprint import pprint
sys.path.insert(0, r"c:\Users\Usuario\OneDrive\Desktop\proyecto IA\Proyecto2\machine-learning\cheapy-backend")

from cheapy_scraper.pipelines import DataCleaningPipeline

pipeline = DataCleaningPipeline()

examples = [
    '(1.012)',
    '+1.012 vendidos',
    '+50 vendidos',
    '1.012K',
    '1.2K',
    '1.5M',
    '(1012)',
    '+1,012',
    '4.9 | +50 vendidos',
    '| +50 vendidos',
    'Más de 1.000',
    '10mil',
    '+10mil vendidos',
    '10 mil vendidos',
    '⭐ 4.6 (10000000)'
]

for s in examples:
    item = {
        'reviews_count_str': s,
        'price': None,
        'rating_str': None,
        'currency_code': 'ARS',
        'country_code': 'AR'
    }
    out = pipeline.process_item(item, spider=None)
    print(f"{s!r} -> reviews_count: {out.get('reviews_count')}")
