import os
import django
import pickle
import torch
import clip
from PIL import Image
from pathlib import Path
from django.utils import timezone

# --- ИНИЦИАЛИЗАЦИЯ DJANGO ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "outfit_django.settings")
django.setup()

from recommendations.models import ClothingItem

# --- CLIP ---
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

# --- АБСОЛЮТНЫЙ ПУТЬ (🔥 ФИКС) ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "raw"


def run_import():
    print("🚀 Начинаю импорт данных...")

    categories = ["tops", "bottoms", "shoes", "accessories"]
    genders = ["M", "F"]
    count = 0

    for gender in genders:
        for cat in categories:
            folder = DATA_DIR / gender / cat

            print(f"\n📁 Проверяю: {folder}")

            if not folder.exists():
                print("❌ Папка не найдена")
                continue

            # 🔥 РЕКУРСИВНЫЙ ПОИСК (фикс)
            files = list(folder.rglob("*"))
            print(f"📊 Найдено файлов: {len(files)}")

            for img_path in files:
                if img_path.suffix.lower() not in ['.jpg', '.jpeg', '.png', '.webp']:
                    continue

                try:
                    print(f"👉 Обрабатываю: {img_path.name}")

                    # --- имя ---
                    pretty_name = img_path.stem.replace('-', ' ').replace('_', ' ').title()

                    # --- CLIP ---
                    image = preprocess(Image.open(img_path)).unsqueeze(0).to(device)
                    with torch.no_grad():
                        emb = model.encode_image(image).cpu().numpy().flatten()

                    # 🔥 КЛЮЧ = external_id (а не image_path)
                    external_id = img_path.stem

                    ClothingItem.objects.update_or_create(
                        external_id=external_id,
                        defaults={
                            'name': pretty_name,
                            'category': cat,
                            'gender': gender,
                            'image_path': str(img_path).replace("\\", "/"),
                            'embedding': pickle.dumps(emb),
                            'color_name': "unknown",
                            'color_rgb': [128, 128, 128],
                            'is_active': True
                        }
                    )

                    count += 1
                    if count % 20 == 0:
                        print(f"✅ Обработано {count}")

                except Exception as e:
                    print(f"❌ Ошибка {img_path.name}: {e}")

    print(f"\n✨ ГОТОВО! Загружено: {count}")
    print("👉 Дальше: python build_index.py")


if __name__ == "__main__":
    run_import()