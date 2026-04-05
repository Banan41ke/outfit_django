"""Обработчики фото"""
from pathlib import Path

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode

from telegram_bot.config import MESSAGES, TEMP_DIR
from telegram_bot.keyboards.inline import (
    category_selection_keyboard,
    single_item_keyboard,
    main_menu_keyboard
)
from telegram_bot.services.image_processor import ImageProcessor
from telegram_bot.services.api_client import analyze_photo
from telegram_bot.utils.states import PhotoUpload


router = Router()

image_processor = ImageProcessor(TEMP_DIR)


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, bot: Bot):
    """Обработка загруженного фото"""
    photo = message.photo[-1]

    if photo.file_size > 20 * 1024 * 1024:
        await message.answer(MESSAGES['file_too_large'])
        return

    processing_msg = await message.answer("⏳ Скачиваю фото...")

    local_path = await image_processor.download_photo(photo.file_id, bot)
    if not local_path:
        await processing_msg.edit_text(MESSAGES['error'].format(error="Не удалось скачать фото"))
        return

    is_valid, error_msg = image_processor.validate_image(local_path)
    if not is_valid:
        await processing_msg.edit_text(MESSAGES['error'].format(error=error_msg))
        image_processor.cleanup(local_path)
        return

    optimized_path = image_processor.optimize_image(local_path)
    detected_category = 'tops'

    await state.set_state(PhotoUpload.WAITING_CATEGORY)
    await state.update_data(
        photo_path=str(optimized_path),
        photo_file_id=photo.file_id,
        query_category=detected_category,
        recommendations=None,
        category_indices={}
    )

    result = await analyze_photo(optimized_path, detected_category)

    gender_emoji = {'M': '👨', 'F': '👩', 'U': '👤'}
    gender_text = result['gender_ru']
    confidence = result['gender_confidence']

    # Показываем статистику источников если есть
    sources = result.get('sources', {})
    source_info = ""
    if sources:
        source_info = f"\n📊 Источники: 🏠 {sources.get('local', 0)} локальных, 🌐 {sources.get('database', 0)} из парсера"

    await processing_msg.edit_text(
        f"✅ <b>Фото получено!</b>\n\n"
        f"Категория: <b>{detected_category.upper()}</b>\n"
        f"Пол: {gender_emoji[result['gender']]} <b>{gender_text}</b> "
        f"({confidence:.0%}){source_info}\n\n"
        f"Что подобрать к этой вещи?",
        parse_mode=ParseMode.HTML,
        reply_markup=category_selection_keyboard(detected_category)
    )

    await state.update_data(gender_result=result)
    image_processor.cleanup(local_path)


@router.callback_query(PhotoUpload.WAITING_CATEGORY, F.data.startswith("recommend:"))
async def show_single_recommendation(callback: CallbackQuery, state: FSMContext):
    """Показывает одну рекомендацию выбранной категории"""
    await callback.answer()

    target_category = callback.data.split(":")[1]
    data = await state.get_data()
    photo_path = Path(data.get('photo_path'))
    query_category = data.get('query_category')
    recommendations = data.get('recommendations')

    if not recommendations:
        await callback.message.edit_text(
            "🔍 <b>Подбираю сочетания...</b>",
            parse_mode=ParseMode.HTML
        )

        result = await analyze_photo(photo_path, query_category)

        if not result['success']:
            await callback.message.edit_text(
                MESSAGES['error'].format(error=result.get('error', 'Неизвестная ошибка'))
            )
            return

        recommendations = result['recommendations']
        await state.update_data(recommendations=recommendations)

    if target_category == 'all':
        await show_all_categories(callback.message, recommendations, state)
    else:
        category_indices = data.get('category_indices', {})
        current_index = category_indices.get(target_category, 0)
        items = recommendations.get(target_category, [])

        if target_category in category_indices and current_index + 1 < len(items):
            next_index = current_index + 1
        else:
            next_index = current_index

        category_indices[target_category] = next_index
        await state.update_data(category_indices=category_indices)

        await show_single_item(callback.message, target_category, recommendations, state, next_index)


async def show_single_item(message, category: str, recommendations: dict, state: FSMContext, index: int):
    """Показывает один товар с навигацией и данными из БД"""
    items = recommendations.get(category, [])

    if not items or index >= len(items):
        await message.answer(
            f"😔 К сожалению, нет рекомендаций для категории <b>{category}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu_keyboard()
        )
        return

    item = items[index]

    from recommendations.templatetags.image_tags import image_url
    url_path = image_url(item['filename'], category)
    img_path = Path("data") / "raw" / category / Path(url_path).name

    data = await state.get_data()
    category_indices = data.get('category_indices', {})
    category_indices[category] = index
    await state.update_data(category_indices=category_indices)

    await state.set_state(PhotoUpload.VIEWING_RESULTS)

    # ← ЗДЕСЬ ДОБАВЛЕН ЭМОДЗИ ИСТОЧНИКА
    source_emoji = {'local': '🏠', 'parser': '🌐'}.get(item.get('source'), '🏠')

    gender_emoji = item.get('gender_emoji', '👤')
    gender_text = {'M': 'Мужское', 'F': 'Женское', 'U': 'Унисекс', 'unknown': 'Не указан'}.get(
        item.get('gender_match', 'unknown'), 'Не указан'
    )

    product_name = item.get('name', 'Без названия')
    if product_name == 'Без названия' and item.get('filename'):
        product_name = item['filename'].replace('.jpg', '').replace('.webp', '')[:30]

    # ← ЗДЕСЬ ДОБАВЛЕН ЭМОДЗИ ИСТОЧНИКА В НАЧАЛО
    caption = (
        f"{source_emoji} <b>{product_name}</b>\n"
        f"{gender_emoji} <i>{gender_text}</i>\n\n"
        f"Категория: <b>{category.upper()}</b> — вариант {index + 1} из {len(items)}\n"
        f"Совместимость: <b>{item['similarity_score']:.0f}%</b>\n"
    )

    if item.get('color_name') and item['color_name'] != 'unknown':
        caption += f"🎨 Цвет: {item['color_name']}\n"

    if item.get('price') and item['price'] != 'Цена не указана':
        caption += f"💰 Цена: {item['price']}\n"

    if item.get('store') and item['store'] != 'Unknown':
        caption += f"🏪 Магазин: {item['store']}\n"

    if item.get('product_url'):
        caption += f"\n🔗 <a href='{item['product_url']}'>Смотреть на сайте</a>"

    if img_path.exists():
        await message.answer_photo(
            photo=FSInputFile(img_path),
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=single_item_keyboard(str(item['id']), category),
            disable_web_page_preview=True
        )
    else:
        await message.answer(
            f"📦 {item['filename']}\n\n{caption}",
            parse_mode=ParseMode.HTML,
            reply_markup=single_item_keyboard(str(item['id']), category),
            disable_web_page_preview=True
        )


async def show_all_categories(message, recommendations: dict, state: FSMContext):
    """Показывает по одному предмету из каждой категории"""
    cat_names = {
        'bottoms': '👖 Низ',
        'shoes': '👟 Обувь',
        'accessories': '🎒 Аксессуары'
    }

    await message.answer(
        "✨ <b>Ваш образ:</b>",
        parse_mode=ParseMode.HTML
    )

    for cat, items in recommendations.items():
        if not items or cat == 'tops':
            continue

        item = items[0]

        from recommendations.templatetags.image_tags import image_url
        url_path = image_url(item['filename'], cat)
        img_path = Path("data") / "raw" / cat / Path(url_path).name

        # ← ЗДЕСЬ ТОЖЕ ДОБАВЛЕН ЭМОДЗИ ИСТОЧНИКА
        source_emoji = {'local': '🏠', 'parser': '🌐'}.get(item.get('source'), '🏠')

        caption = (
            f"{source_emoji} <b>{cat_names.get(cat, cat)}</b>\n"
            f"Совместимость: <b>{item['similarity_score']:.0f}%</b>"
        )

        if img_path.exists():
            await message.answer_photo(
                photo=FSInputFile(img_path),
                caption=caption,
                parse_mode=ParseMode.HTML
            )
        else:
            await message.answer(caption, parse_mode=ParseMode.HTML)

    await message.answer(
        "🎯 <b>Готово!</b>\n\nХотите подобрать ещё что-то?",
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )

    await state.clear()


@router.callback_query(PhotoUpload.VIEWING_RESULTS, F.data.startswith("next:"))
async def show_next_item(callback: CallbackQuery, state: FSMContext):
    """Показывает следующий вариант той же категории"""
    await callback.answer()

    category = callback.data.split(":")[1]
    data = await state.get_data()
    recommendations = data.get('recommendations')

    category_indices = data.get('category_indices', {})
    current_index = category_indices.get(category, 0)

    next_index = current_index + 1
    items = recommendations.get(category, [])

    if next_index >= len(items):
        await callback.answer("Это последний вариант!", show_alert=True)
        return

    category_indices[category] = next_index
    await state.update_data(category_indices=category_indices)

    await show_single_item(callback.message, category, recommendations, state, next_index)


@router.callback_query(F.data == "back:categories")
async def back_to_categories(callback: CallbackQuery, state: FSMContext):
    """Возврат к выбору категорий"""
    await callback.answer()

    data = await state.get_data()
    query_category = data.get('query_category', 'tops')

    await callback.message.answer(
        "Что подобрать к этой вещи?",
        parse_mode=ParseMode.HTML,
        reply_markup=category_selection_keyboard(query_category)
    )

    await state.set_state(PhotoUpload.WAITING_CATEGORY)


@router.callback_query(F.data == "new_photo")
async def new_photo(callback: CallbackQuery, state: FSMContext):
    """Новое фото"""
    await state.clear()
    await callback.message.answer(
        "📸 <b>Отправьте новое фото</b>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()