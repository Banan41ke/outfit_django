"""Inline клавиатуры"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def category_selection_keyboard(query_category: str) -> InlineKeyboardMarkup:
    """
    Клавиатура выбора категории для сочетания
    Исключаем категорию загруженной вещи
    """
    buttons = []

    # Определяем доступные категории (исключаем загруженную)
    all_categories = {
        'tops': ('👕 Верх', 'tops'),
        'bottoms': ('👖 Низ', 'bottoms'),
        'shoes': ('👟 Обувь', 'shoes'),
        'accessories': ('🎒 Аксессуары', 'accessories')
    }

    available = [(name, cat) for cat, (name, _) in all_categories.items() if cat != query_category]

    # Делаем по 2 кнопки в ряд
    row = []
    for name, cat in available:
        row.append(InlineKeyboardButton(text=name, callback_data=f"recommend:{cat}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    # Кнопка "Все сочетания"
    buttons.append([
        InlineKeyboardButton(text="✨ Показать всё", callback_data="recommend:all")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def single_item_keyboard(item_id: str, category: str) -> InlineKeyboardMarkup:
    """Клавиатура для одного товара"""
    buttons = [
        [
            InlineKeyboardButton(text="🔄 Другой вариант", callback_data=f"next:{category}"),
            InlineKeyboardButton(text="❤️ В избранное", callback_data=f"fav:{item_id}"),
        ],
        [
            InlineKeyboardButton(text="⬅️ Назад к категориям", callback_data="back:categories"),
        ],
        [
            InlineKeyboardButton(text="📸 Новое фото", callback_data="new_photo"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню"""
    buttons = [
        [
            InlineKeyboardButton(text="📸 Загрузить фото", callback_data="upload"),
            InlineKeyboardButton(text="📋 История", callback_data="history"),
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="❓ Помощь", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)