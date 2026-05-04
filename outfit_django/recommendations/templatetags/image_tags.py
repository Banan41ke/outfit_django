import os
from django import template
from django.conf import settings

register = template.Library()


@register.filter(name='image_url')
def get_clothing_image(item):
    if not item:
        return "/static/images/logo.png"

    if isinstance(item, dict):
        path = item.get("image_path", "")
    else:
        path = getattr(item, "image_path", "")

    if not path:
        return "/static/images/logo.png"

    path = path.replace("\\", "/")

    # === ЕСЛИ это путь из data/raw ===
    if "data/raw/" in path:
        path = path.split("data/raw/")[-1]
        return f"/dataset/{path}"   # 👈 отдельный URL

    # === ЕСЛИ это уже media (пользователь) ===
    return f"{settings.MEDIA_URL}{path}"


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)