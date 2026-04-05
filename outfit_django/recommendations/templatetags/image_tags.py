from django import template
from django.conf import settings
from pathlib import Path
import os

register = template.Library()


@register.filter(name='image_url')
def image_url(filename, category):
    base_dir = Path(settings.BASE_DIR) / 'data' / 'raw' / category
    filename = os.path.basename(str(filename))

    print(f"\n🔍 image_url: filename={filename}, category={category}")

    extensions = ['.webp', '.jpg', '.jpeg', '.png', '.gif']

    # Имя без расширения
    name_without_ext = filename
    for ext in extensions:
        if filename.lower().endswith(ext):
            name_without_ext = filename[:-len(ext)]
            break

    print(f"   name_without_ext (after ext removal): {name_without_ext}")

    # Убираем префикс категории
    prefix = f"{category}_"
    if name_without_ext.startswith(prefix):
        name_without_ext = name_without_ext[len(prefix):]
        print(f"   name_without_ext (after prefix removal): {name_without_ext}")

    # Ищем файл
    for ext in extensions:
        full_path = base_dir / f"{name_without_ext}{ext}"
        exists = full_path.exists()
        print(f"   checking: {full_path} -> {exists}")
        if exists:
            result = f"/data/raw/{category}/{name_without_ext}{ext}"
            print(f"   ✅ FOUND: {result}")
            return result

    result = f"/data/raw/{category}/{name_without_ext}.webp"
    print(f"   ❌ NOT FOUND, fallback: {result}")
    return result