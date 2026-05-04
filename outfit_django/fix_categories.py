import os
import django

# инициализация Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "outfit_django.settings")
django.setup()

from recommendations.models import ClothingItem
from outfit_django.src.feature_extractor import CLIPEncoder

encoder = CLIPEncoder()

print("🚀 Старт исправления категорий...")

for item in ClothingItem.objects.all():
    try:
        pred_category, conf = encoder.predict_category(item.image_path)

        if conf > 0.8 and pred_category != item.category:
            print(f"FIX DB: {item.id} {item.category} → {pred_category} ({conf:.2f})")

            item.category = pred_category
            item.save()

    except Exception as e:
        print(f"⚠️ Ошибка {item.id}: {e}")

print("✅ Готово!")