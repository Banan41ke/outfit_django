import os
import re
from django import template
from django.conf import settings

register = template.Library()


@register.filter(name='image_url')
def get_clothing_image(item):
    if not item:
        return "/static/images/logo.png"

    file_name = ""
    image_url = ""
    category = ""
    gender = ""

    # 0. БЫСТРЫЙ ВОЗВРАТ: если есть полный путь и файл существует
    if isinstance(item, dict):
        full_path = item.get('image_path', '')
        if full_path and os.path.exists(os.path.join(settings.BASE_DIR, full_path.replace('/', os.sep))):
            return f"/{full_path.replace(os.sep, '/')}"

        file_name = item.get('image_path') or item.get('filename') or item.get('name') or ""
        image_url = item.get('image_url', '')
        category = item.get('category', '')
        gender = item.get('gender', '')
    else:
        file_name = getattr(item, 'image_path', getattr(item, 'name', ""))
        image_url = getattr(item, 'image_url', '')
        category = getattr(item, 'category', '')
        gender = getattr(item, 'gender', '')

    # 1. Внешний URL (приоритет)
    if image_url and (image_url.startswith('http://') or image_url.startswith('https://')):
        return image_url

    if not file_name:
        return "/static/images/logo.png"

    file_name = str(file_name).replace('\\', '/').split('/')[-1]
    base_name = os.path.splitext(file_name)[0]  # без расширения

    # 2. Определяем пол из имени файла если не указан
    if not gender:
        match = re.search(r'[_\-.]([MF])[_\-.]', file_name)
        if match:
            gender = match.group(1)

    # 3. Ищем файл с ЛЮБЫМ расширением в разных папках
    search_dirs = []
    if gender:
        search_dirs.extend([
            f"data/raw/{gender}/{category}",
            f"data/raw/{gender.upper()}/{category}",
        ])
    search_dirs.extend([
        f"data/raw/M/{category}",
        f"data/raw/F/{category}",
        f"data/raw/{category}",
        f"parsers/data",
        f"parsers/data/{category}",
        f"media/temp",
    ])

    for search_dir in search_dirs:
        full_dir = os.path.join(settings.BASE_DIR, search_dir)
        if not os.path.exists(full_dir):
            continue

        # Ищем с любым расширением
        for ext in ['.webp', '.jpg', '.jpeg', '.png']:
            test_path = os.path.join(full_dir, base_name + ext)
            if os.path.exists(test_path):
                rel = os.path.relpath(test_path, settings.BASE_DIR)
                return f"/{rel.replace(os.sep, '/')}"

        # Или точное совпадение
        test_path = os.path.join(full_dir, file_name)
        if os.path.exists(test_path):
            rel = os.path.relpath(test_path, settings.BASE_DIR)
            return f"/{rel.replace(os.sep, '/')}"

    # 4. Рекурсивный поиск в data/raw (последний шанс)
    base_raw = os.path.join(settings.BASE_DIR, 'data', 'raw')
    if os.path.exists(base_raw):
        for root, dirs, files in os.walk(base_raw):
            # Ищем по базовому имени (без расширения)
            for f in files:
                if f.startswith(base_name):
                    rel = os.path.relpath(os.path.join(root, f), settings.BASE_DIR)
                    return f"/{rel.replace(os.sep, '/')}"

    print(f"--- [DEBUG] Файл НЕ НАЙДЕН: {file_name} | gender: {gender} | category: {category}")
    print(f"  Проверены папки: {search_dirs}")
    return "/static/images/logo.png"


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)