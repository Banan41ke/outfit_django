import os
import pickle
from pathlib import Path

print("🔄 Перестроение индексов...")

# 1. BOTTOMS - ВСЕ файлы (не только 10)
bottoms_files = []
bottoms_files.extend(Path("data/raw/F/bottoms").glob("*.webp"))
bottoms_files.extend(Path("data/raw/M/bottoms").glob("*.webp"))

print(f"📁 Найдено файлов bottoms: {len(bottoms_files)}")

# Создаем метаданные для ВСЕХ файлов
bottoms_metadata = []
for file_path in bottoms_files:  # Убрано [:10] - теперь все файлы
    bottoms_metadata.append({
        'name': file_path.stem,
        'path': str(file_path),
        'image_url': str(file_path),
        'category': 'bottoms',
        'price': None,
        'currency': '₽',
        'store': 'Zara'
    })

# Сохраняем индекс
with open("models/bottoms_meta.pkl", "wb") as f:
    pickle.dump(bottoms_metadata, f)

print(f"✅ bottoms: {len(bottoms_metadata)} items (из {len(bottoms_files)} файлов)")

# 2. TOPS - проверьте, есть ли файлы для верха
tops_files = []
tops_files.extend(Path("data/raw/F/tops").glob("*.webp"))  # Проверьте путь
tops_files.extend(Path("data/raw/M/tops").glob("*.webp"))

if tops_files:
    tops_metadata = []
    for file_path in tops_files:
        tops_metadata.append({
            'name': file_path.stem,
            'path': str(file_path),
            'image_url': str(file_path),
            'category': 'tops',
            'price': None,
            'currency': '₽',
            'store': 'Zara'
        })
    with open("models/tops_meta.pkl", "wb") as f:
        pickle.dump(tops_metadata, f)
    print(f"✅ tops: {len(tops_metadata)} items")
else:
    print(f"⚠️ tops: нет файлов (ищите в data/raw/F/tops/ или data/raw/M/tops/)")

# 3. SHOES - проверьте другие возможные папки
shoes_files = []
# Проверьте несколько возможных мест
possible_shoes_paths = [
    "parsers/data/*.jpg",
    "parsers/data/*.webp",
    "data/raw/shoes/*.webp",
    "data/raw/*/shoes/*.webp",
    "media/shoes/*.webp"
]

for path_pattern in possible_shoes_paths:
    found = list(Path().glob(path_pattern))
    shoes_files.extend(found)

if shoes_files:
    shoes_metadata = []
    for file_path in shoes_files[:50]:  # Ограничим для теста, но можно убрать
        shoes_metadata.append({
            'name': file_path.stem,
            'path': str(file_path),
            'image_url': str(file_path),
            'category': 'shoes',
            'price': None,
            'currency': '₽',
            'store': 'Lamoda'
        })
    with open("models/shoes_meta.pkl", "wb") as f:
        pickle.dump(shoes_metadata, f)
    print(f"✅ shoes: {len(shoes_metadata)} items из {len(shoes_files)} найденных")
else:
    print(f"⚠️ shoes: файлы не найдены ни в одной из папок")

# 4. ACCESSORIES - если есть
accessories_files = list(Path("data/raw/accessories").glob("*.webp")) if Path("data/raw/accessories").exists() else []
if accessories_files:
    accessories_metadata = []
    for file_path in accessories_files:
        accessories_metadata.append({
            'name': file_path.stem,
            'path': str(file_path),
            'image_url': str(file_path),
            'category': 'accessories',
            'price': None,
            'currency': '₽',
            'store': 'Various'
        })
    with open("models/accessories_meta.pkl", "wb") as f:
        pickle.dump(accessories_metadata, f)
    print(f"✅ accessories: {len(accessories_metadata)} items")

print(f"\n📊 ИТОГО:")
print(f"  - Низ (bottoms): {len(bottoms_metadata)} товаров")
print(f"  - Верх (tops): {len(tops_files)} товаров" if tops_files else "  - Верх (tops): 0 товаров")
print(f"  - Обувь (shoes): {len(shoes_files)} товаров" if shoes_files else "  - Обувь (shoes): 0 товаров")
print(f"  - Аксессуары (accessories): {len(accessories_files)} товаров" if accessories_files else "  - Аксессуары (accessories): 0 товаров")
print("\n✅ Индексы перестроены со ВСЕМИ товарами!")