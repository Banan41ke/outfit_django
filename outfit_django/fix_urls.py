import json
import os
import sys
from pathlib import Path

# Инициализация Django
base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')

import django

django.setup()

from recommendations.models import ClothingItem

# Пробуем оба пути к JSON
json_paths = [
    base_dir / "parsers" / "temp_items.json",
    base_dir / "temp_items.json",
]

items = None
for path in json_paths:
    if path.exists():
        print(f"Найден JSON: {path}")
        with open(path, "r", encoding="utf-8") as f:
            items = json.load(f)
        break

if not items:
    print("❌ JSON не найден!")
    exit()

updated = 0
not_found = 0
for item_data in items:
    url = item_data.get('product_url', '').strip()
    if not url:
        continue

    # Определяем store из URL или id
    store = item_data.get('store', '')
    if not store:
        if 'lamoda' in url:
            store = 'Lamoda'
        elif 'madfashion' in url:
            store = 'MadFashion'
        else:
            store = 'Unknown'

    external_id = item_data['id']

    cnt = ClothingItem.objects.filter(external_id=external_id).update(
        product_url=url,
        store=store
    )
    if cnt:
        updated += cnt
        print(f"✅ Updated: {external_id} | store={store} | url={url[:50]}...")
    else:
        not_found += 1
        print(f"❌ Not found in DB: {external_id}")

print(f"\n=== ИТОГ ===")
print(f"Обновлено записей: {updated}")
print(f"Не найдено в БД: {not_found}")
print(f"Всего в JSON: {len(items)}")