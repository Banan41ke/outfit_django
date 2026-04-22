import os
import django
import pickle
import numpy as np
import faiss
from pathlib import Path

# Инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "outfit_django.settings")
django.setup()

from recommendations.models import ClothingItem

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)


def build_index_for_category(category):
    # Берем ВСЕ объекты категории, у которых есть эмбеддинг
    items = ClothingItem.objects.filter(category=category, embedding__isnull=False)

    print(f"🔍 Найдено в базе для {category}: {items.count()} предметов")

    embeddings = []
    metadata = []

    for item in items:
        try:
            emb = pickle.loads(item.embedding)
            # Убеждаемся, что эмбеддинг — это numpy array
            if isinstance(emb, list):
                emb = np.array(emb)

            embeddings.append(emb)

            # ВАЖНО: Добавляем 'name', чтобы фильтр image_url в шаблоне работал
            filename = Path(item.image_path).name
            metadata.append({
                "id": item.id,
                "name": filename,
                "filename": filename,
                "raw_filename": filename,
                "gender": item.gender,
                "image_path": item.image_path,
                "category": item.category,  # 🔥 ВОТ ЭТО ГЛАВНОЕ
                "color_name": item.color_name,
                "color_rgb": item.color_rgb,
                "style": "casual",
            })
        except Exception as e:
            print(f"⚠️ Ошибка обработки предмета {item.id}: {e}")

    if not embeddings:
        print(f"❌ Нет данных для создания индекса {category}")
        return

    embeddings = np.array(embeddings).astype("float32")

    # 🔥 ВОТ ЗДЕСЬ
    faiss.normalize_L2(embeddings)

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(MODELS_DIR / f"{category}.index"))

    with open(MODELS_DIR / f"{category}_meta.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ Успешно сохранено: {len(metadata)} предметов в индексе {category}")


def main():
    categories = ["tops", "bottoms", "shoes", "accessories"]
    for cat in categories:
        build_index_for_category(cat)


if __name__ == "__main__":
    main()