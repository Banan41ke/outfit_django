import sys
import os
import pickle
import requests
import json
import subprocess
import time
from pathlib import Path
from PIL import Image
from io import BytesIO
# --- ИСПРАВЛЕНИЕ ПУТЕЙ ---
# Определяем корень проекта (на уровень выше текущей папки parsers)
current_file = Path(__file__).resolve()
base_dir = current_file.parent.parent
sys.path.insert(0, str(base_dir))

# Настройка Django окружения
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')

def load_image_safe(img_url: str):
    # 🔥 чистим URL
    img_url = img_url.strip().replace('%20', '')

    for attempt in range(3):
        try:
            response = requests.get(img_url, timeout=10)

            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}")

            image = Image.open(BytesIO(response.content)).convert("RGB")
            return image

        except Exception as e:
            print(f"⚠️ Попытка {attempt+1} не удалась: {e}")
            time.sleep(1)

    return None


# --- ФУНКЦИЯ ДЛЯ ЗАГРУЗКИ В БД (Этап 2) ---
def process_json_to_db():
    import django
    django.setup()
    from recommendations.models import ClothingItem
    from outfit_django.src.feature_extractor import CLIPEncoder

    print("🧹 Очистка старых данных MadFashion из БД...")
    ClothingItem.objects.filter(store="MadFashion").delete()

    encoder = CLIPEncoder()

    if not os.path.exists("temp_items.json"):
        print("❌ Файл temp_items.json не найден!")
        return

    # Станет (явный путь к parsers):
    json_path = base_dir / "parsers" / "temp_items.json"
    # или если парсер сохраняет в корень:
    json_path = base_dir / "temp_items.json"

    with open(json_path, "r", encoding="utf-8") as f:
        items = json.load(f)

    print(f"🔄 Начинаю обработку {len(items)} товаров (скачивание + CLIP)...")

    for item_data in items:
        # Формируем путь для сохранения фото
        rel_path = Path("data") / "raw" / item_data['gender'] / item_data['category'] / f"{item_data['id']}.jpg"
        image_path = base_dir / rel_path

        try:
            image = load_image_safe(item_data['image_url'])

            if image is None:
                print(f"❌ Пропуск {item_data['id']}")
                continue

            image_path.parent.mkdir(parents=True, exist_ok=True)
            image.save(image_path)

            # CLIP
            emb = encoder.encode_image(str(image_path))
            emb_bytes = pickle.dumps(emb) if emb is not None else None

            ClothingItem.objects.create(
                external_id=item_data['id'],
                name=item_data['name'],
                category=item_data['category'],
                gender=item_data['gender'],
                style_name=item_data.get('style', 'Casual'),
                image_path=str(rel_path),
                image_url=item_data['image_url'],
                product_url=item_data['product_url'],
                store="MadFashion",
                price=item_data.get('price', 0),
                currency="BYN",
                embedding=emb_bytes
            )

            print(f"✅ Сохранено: {item_data['name'][:30]}")
            time.sleep(0.2)

        except Exception as e:
            print(f"❌ Ошибка на {item_data['id']}: {e}")


# --- ЭТАП 1: СБОР ССЫЛОК (Этап 1) ---
def run_parsing():
    # Импорт внутри функции, чтобы sys.path успел обновиться
    try:
        from parsers.mad_fashion_parser import MadFashionParser
    except ModuleNotFoundError:
        # Если запущен из папки parsers, пробуем прямой импорт
        from mad_fashion_parser import MadFashionParser

    all_items_data = []
    categories = ["tops", "bottoms", "accessories"]

    with MadFashionParser() as parser:
        for category in categories:
            for gender in ['M', 'F']:
                print(f"\n🔍 MadFashion | {category} | Пол: {gender}")

                # Явно получаем список
                result = parser.parse_category(category=category, gender=gender, pages=2)

                if result:
                    print(f"📦 Добавляю {len(result)} объектов в общий список...")
                    for item in result:
                        all_items_data.append({
                            "id": item.id,
                            "name": item.name,
                            "category": item.category,
                            "gender": item.gender,
                            "image_url": item.image_url,
                            "product_url": item.product_url,
                            "style": item.color,
                            "price": item.price
                        })
                else:
                    print(f"⚠️ Категория {category} вернула пустой список.")
    time.sleep(0.2)
    with open("temp_items.json", "w", encoding="utf-8") as f:
        json.dump(all_items_data, f, ensure_ascii=False, indent=4)
    print(f"\n✅ Всего собрано {len(all_items_data)} ссылок.")


if __name__ == "__main__":
    if "--db-only" in sys.argv:
        process_json_to_db()
    else:
        print("🚀 ЭТАП 1: СБОР ССЫЛОК С MADFASHION...")
        run_parsing()

        print("\n🚀 ЭТАП 2: ЗАГРУЗКА В БД И ОБРАБОТКА CLIP...")
        # Запускаем второй этап в чистом процессе
        subprocess.run([sys.executable, str(current_file), "--db-only"])

        print("\n🎉 ВСЕ ЭТАПЫ ЗАВЕРШЕНЫ УСПЕШНО!")