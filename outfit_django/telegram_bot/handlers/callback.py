"""Обработчики callback кнопок"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.enums import ParseMode

from telegram_bot.keyboards.inline import (
    main_menu_keyboard,
    category_selection_keyboard  # ← исправлено
)


router = Router()


@router.callback_query(F.data == "new_photo")
async def new_photo(callback: CallbackQuery):
    """Новое фото"""
    await callback.message.answer(
        "📸 <b>Отправьте новое фото</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "history")
async def show_history(callback: CallbackQuery):
    """Показать историю"""
    # TODO: Подключить БД
    await callback.message.answer(
        "📋 <b>История запросов</b>\n\n"
        "Пока здесь пусто...\n"
        "Сделайте первый запрос!",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery):
    """Настройки"""
    await callback.message.answer(
        "⚙️ <b>Настройки профиля</b>\n\n"
        "Здесь можно будет указать:\n"
        "• Размер одежды\n"
        "• Предпочтительный стиль\n"
        "• Бюджет\n\n"
        "В разработке 🚧",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("fav:"))
async def add_to_favorites(callback: CallbackQuery):
    """Добавить в избранное"""
    item_id = callback.data.split(":")[1]
    # TODO: Сохранить в БД
    await callback.answer("❤️ Добавлено в избранное!", show_alert=True)


@router.callback_query(F.data.startswith("buy:"))
async def where_to_buy(callback: CallbackQuery):
    """Где купить"""
    item_id = callback.data.split(":")[1]
    await callback.message.answer(
        "🛒 <b>Где купить</b>\n\n"
        "Ссылки на магазины:\n"
        "• Zara — в разработке\n"
        "• H&M — в разработке\n"
        "• Lamoda — в разработке\n\n"
        "Скоро добавим! 🚀",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("more:"))
async def more_variants(callback: CallbackQuery):
    """Ещё варианты"""
    category = callback.data.split(":")[1]
    await callback.message.answer(
        f"🔄 <b>Ещё варианты для {category}</b>\n\n"
        "Загружаю...",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()