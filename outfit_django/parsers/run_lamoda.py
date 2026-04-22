import sys
import os
import json
import subprocess
from pathlib import Path

base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')


def run_parsing():
    from lamoda_parser import LamodaParser

    all_items = []

    with LamodaParser() as parser:
        for gender in ['M', 'F']:
            print(f"\n🔍 Lamoda | shoes | Пол: {gender}")
            result = parser.parse_category(category='shoes', gender=gender, pages=1)
            if result:
                for item in result:
                    all_items.append({
                        "id": item.id,
                        "name": item.name,
                        "category": item.category,
                        "gender": item.gender,
                        "image_url": item.image_url,
                        "product_url": item.product_url,
                        "style": item.color,
                        "price": item.price,
                        "store": item.store
                    })
                print(f"📦 Добавлено: {len(result)}")

    with open("lamoda_items.json", "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Всего собрано: {len(all_items)}")


if __name__ == "__main__":
    run_parsing()