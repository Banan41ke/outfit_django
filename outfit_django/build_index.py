import os
import django
import pickle
import numpy as np
import faiss
from pathlib import Path

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "outfit_django.settings")
django.setup()

from recommendations.models import ClothingItem

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

CATEGORIES = ["tops", "bottoms", "shoes", "accessories"]


def main():
    print("🚀 Сборка индексов")

    items = ClothingItem.objects.filter(embedding__isnull=False)
    print(f"🔍 Всего предметов: {items.count()}")

    category_buckets = {cat: [] for cat in CATEGORIES}
    metadata_buckets = {cat: [] for cat in CATEGORIES}

    for item in items:
        try:
            if not item.embedding:
                continue

            emb = pickle.loads(item.embedding)

            category = item.category

            if category not in CATEGORIES:
                print(f"❌ Пропущен (категория): {item.id}")
                continue

            filename = Path(item.image_path).name

            category_buckets[category].append(emb)

            metadata_buckets[category].append({
                "id": item.id,
                "name": filename,
                "filename": filename,
                "image_path": item.image_path,
                "category": category,
                "gender": item.gender,
                "color_name": item.color_name,
                "color_rgb": item.color_rgb,
                "style": "casual",
            })

        except Exception as e:
            print(f"⚠️ Ошибка {item.id}: {e}")

    # === СОЗДАНИЕ FAISS ИНДЕКСОВ ===
    for category in CATEGORIES:
        embeddings = category_buckets[category]

        if len(embeddings) == 0:
            print(f"❌ {category}: пусто")
            continue

        embeddings = np.array(embeddings).astype("float32")
        faiss.normalize_L2(embeddings)

        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)

        faiss.write_index(index, str(MODELS_DIR / f"{category}.index"))

        with open(MODELS_DIR / f"{category}_meta.pkl", "wb") as f:
            pickle.dump(metadata_buckets[category], f)

        print(f"✅ {category}: {len(metadata_buckets[category])} предметов")

    print("🎉 Готово!")


if __name__ == "__main__":
    main()