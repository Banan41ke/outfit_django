"""FSM состояния для бота"""
from aiogram.fsm.state import State, StatesGroup


class UserState(StatesGroup):
    """Состояния пользователя"""
    IDLE = State()
    UPLOADING_PHOTO = State()
    SELECTING_CATEGORY = State()
    VIEWING_RESULTS = State()

class PhotoUpload(StatesGroup):
    """Состояния загрузки фото"""
    WAITING_PHOTO = State()
    WAITING_CATEGORY = State()  # Выбор категории (низ/обувь/аксессуары)
    VIEWING_RESULTS = State()   # Просмотр одного товара с навигацией