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


def build_index_for_category(category):
    items = ClothingItem.objects.filter(category=category, embedding__isnull=False)

    embeddings = []
    metadata = []

    for item in items:
        try:
            emb = pickle.loads(item.embedding)
            embeddings.append(emb)
            metadata.append({
                "id": item.id,
                "filename": Path(item.image_path).name,
                "raw_filename": Path(item.image_path).name,
                "color_name": item.color_name,
                "color_rgb": item.color_rgb,
                "style": "casual",
            })
        except Exception as e:
            print(f"⚠️ Ошибка эмбеддинга {item.id}: {e}")

    if not embeddings:
        print(f"❌ Нет данных для {category}")
        return

    embeddings = np.array(embeddings).astype("float32")

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    # сохраняем
    faiss.write_index(index, str(MODELS_DIR / f"{category}.index"))

    with open(MODELS_DIR / f"{category}_meta.pkl", "wb") as f:
        pickle.dump(metadata, f)

    print(f"✅ Индекс {category}: {len(metadata)} items")


def main():
    categories = ["tops", "bottoms", "shoes", "accessories"]

    for cat in categories:
        build_index_for_category(cat)


if __name__ == "__main__":
    main()