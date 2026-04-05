import os
import django
import sys
from pathlib import Path

# Настройка Django
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'outfit_django.settings')
django.setup()

from recommendations.models import ClothingItem
from django.db.models import Count


def show_stats():
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ ОДЕЖДЫ\n")

    # 1. Общее количество
    total = ClothingItem.objects.count()
    print(f"Всего товаров в базе: {total}")
    print("-" * 30)

    # 2. Группировка по полу
    print("👫 Распределение по полу:")
    gender_stats = ClothingItem.objects.values('gender').annotate(total=Count('id'))
    gender_map = {'M': 'Мужское', 'F': 'Женское', 'U': 'Унисекс'}
    for stat in gender_stats:
        gender_name = gender_map.get(stat['gender'], stat['gender'])
        print(f"  {gender_name}: {stat['total']}")
    print("-" * 30)

    # 3. Группировка по стилям (то, что ты просил)
    print("👗 Распределение по стилям:")
    style_stats = ClothingItem.objects.values('style_name').annotate(total=Count('id')).order_by('-total')

    for stat in style_stats:
        style = stat['style_name'] if stat['style_name'] else "Не указан"
        print(f"  {style}: {stat['total']}")
    print("-" * 30)

    # 4. Проверка наличия эмбеддингов (CLIP)
    with_emb = ClothingItem.objects.filter(embedding__isnull=False).count()
    print(f"Товаров с CLIP-векторами: {with_emb} из {total}")


if __name__ == "__main__":
    show_stats()