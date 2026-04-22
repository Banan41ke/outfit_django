import json
import os
import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')

import django

django.setup()

from recommendations.models import ClothingItem

# Загружаем JSON
with open("parsers/temp_items.json", "r", encoding="utf-8") as f:
    items = json.load(f)

updated = 0
not_found = 0

for item_data in items:
    external_id = item_data['id']
    url = item_data.get('product_url', '').strip()
    store = item_data.get('store', 'Lamoda')

    if not url:
        continue

    # Обновляем по external_id
    cnt = ClothingItem.objects.filter(external_id=external_id).update(
        product_url=url,
        store=store
    )

    if cnt:
        updated += cnt
        print(f"✅ Updated: {external_id} | {url[:50]}...")
    else:
        not_found += 1
        print(f"❌ Not found: {external_id}")

print(f"\n=== ИТОГ ===")
print(f"Обновлено: {updated}")
print(f"Не найдено: {not_found}")