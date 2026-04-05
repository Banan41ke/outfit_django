"""Обработчики старта и помощи"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode

from telegram_bot.config import MESSAGES
from telegram_bot.keyboards.inline import main_menu_keyboard

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработка /start"""
    user_name = message.from_user.first_name or "друг"

    await message.answer(
        MESSAGES['start'].format(name=user_name),
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработка /help"""
    await message.answer(
        MESSAGES['help'],
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Callback помощь"""
    await callback.message.edit_text(
        MESSAGES['help'],
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "upload")
async def callback_upload(callback: CallbackQuery):
    """Callback загрузить фото"""
    await callback.message.edit_text(
        "📸 <b>Отправьте фото одежды</b>\n\n"
        "Я проанализирую её и подберу сочетания!",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()