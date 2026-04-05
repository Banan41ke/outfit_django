import sys
import os
import pickle
import requests
import json
import subprocess
import time
from pathlib import Path

# Определение путей
current_file = Path(__file__).resolve()
base_dir = current_file.parent.parent
sys.path.insert(0, str(base_dir))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')


# ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ В БД (Вызывается в отдельном процессе)
def process_json_to_db():
    import django
    django.setup()
    from recommendations.models import ClothingItem
    from outfit_django.src.feature_extractor import CLIPEncoder

    print("🧹 Очистка базы данных...")
    ClothingItem.objects.all().delete()

    encoder = CLIPEncoder()

    if not os.path.exists("temp_items.json"):
        print("❌ Файл temp_items.json не найден!")
        return

    with open("temp_items.json", "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"🔄 Начинаю обработку {len(items)} товаров (скачивание + CLIP)...")

    for item_data in items:
        # Проверка на дубликаты внутри базы (на случай пересечения категорий)
        if ClothingItem.objects.filter(id=item_data['id']).exists():
            continue

        # Путь: data/raw/M/shoes/id.jpg или data/raw/F/shoes/id.jpg
        rel_path = Path("data") / "raw" / item_data['gender'] / item_data['category'] / f"{item_data['id']}.jpg"
        image_path = base_dir / rel_path

        # Скачивание
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        try:
            # Небольшая пауза, чтобы сервер картинок не банил
            time.sleep(0.2)

            resp = requests.get(item_data['image_url'], headers=headers, timeout=15)
            if resp.status_code == 200:
                image_path.parent.mkdir(parents=True, exist_ok=True)
                with open(image_path, 'wb') as f:
                    f.write(resp.content)

                # CLIP признак
                emb = encoder.encode_image(str(image_path))
                emb_bytes = pickle.dumps(emb) if emb is not None else None

                # Сохранение в модель
                ClothingItem.objects.create(
                    id=item_data['id'],
                    name=item_data['name'],
                    category=item_data['category'],
                    gender=item_data['gender'],
                    style_name=item_data.get('style', 'Casual'),
                    image_path=str(rel_path),
                    image_url=item_data['image_url'],
                    product_url=item_data['product_url'],
                    store="Lamoda",
                    price=0,
                    currency="BYN",
                    embedding=emb_bytes
                )
                print(f"✅ Сохранено: {item_data['name'][:30]} [{item_data['gender']}]")
        except Exception as e:
            print(f"❌ Ошибка на {item_data['id']}: {e}")


# ЭТАП 1: СБОР ССЫЛОК (Playwright)
def run_parsing():
    from parsers.lamoda_parser import LamodaParser
    all_items_data = []

    with LamodaParser() as parser:
        # ОБХОДИМ ОБА ПОЛА: Мужской и Женский
        for gender in ['M', 'F']:
            print(f"\n🔍 Парсинг категории: shoes | Пол: {gender}")
            items = parser.parse_category(category="shoes", gender=gender, pages=1)

            for item in items:
                all_items_data.append({
                    "id": item.id,
                    "name": item.name,
                    "category": item.category,
                    "gender": item.gender,
                    "image_url": item.image_url,
                    "product_url": item.product_url,
                    "style": item.color  # В LamodaParser стиль кладется в color
                })

    with open("temp_items.json", "w", encoding="utf-8") as f:
        json.dump(all_items_data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Всего собрано {len(all_items_data)} ссылок.")


if __name__ == "__main__":
    # Если запущено с флагом --db-only, выполняем только работу с БД
    if "--db-only" in sys.argv:
        process_json_to_db()
    else:
        # 1. Запускаем парсинг (Этап 1)
        print("🚀 ЭТАП 1: ПАРСИНГ ССЫЛОК С LAMODA...")
        run_parsing()

        # 2. Запускаем СЕБЯ ЖЕ в новом чистом процессе для БД (Этап 2)
        print("🚀 ЭТАП 2: ЗАГРУЗКА В БД И ОБРАБОТКА CLIP...")
        subprocess.run([sys.executable, __file__, "--db-only"])

        print("\n🎉 ВСЕ ЭТАПЫ ЗАВЕРШЕНЫ УСПЕШНО!")