from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from app.bot.utils.func import minutes_to_hours_and_minutes
from app.config import bot
class VerifedCallback(CallbackData, prefix="ver_admin"):
    action: str
    user_id: int = None

def verified_user(user_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Подтвердить",
        callback_data=VerifedCallback(
            action="verified_user_yes",
            user_id=user_id
        ).pack()
    )
    kb.button(
        text="❌ Отклонить",
        callback_data=VerifedCallback(
            action="verified_user_no",
            user_id=user_id
        ).pack()
    )
    kb.adjust(2)
    return kb.as_markup()

class LotConfirmCallback(CallbackData,prefix="lot_confirm"):
    action:str

def lot_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Подтвердить",
        callback_data=LotConfirmCallback(
            action="yes",
        ).pack()
    )
    kb.button(
        text="❌ Отклонить",
        callback_data=LotConfirmCallback(
            action="No",
        ).pack()
    )
    kb.adjust(2)
    return kb.as_markup()


def lot_kb(data:dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text='Фото',url = data.get('photos_link'))
    kb.button(text='Автотека',url = data.get('autoteka_link'))
    kb.button(text='Диагностическая карта',url = data.get('diagnostik_link'))
    kb.button(text='До конца аукциона ' + minutes_to_hours_and_minutes(data.get('time_in_minutes')), callback_data='non_clickable')
    if data.get('current_rate'):
        kb.button(text=f'Текущая ставка: {data.get('current_rate')}', callback_data='non_clickable')
    else:
        kb.button(text='Ставок пока нет', callback_data='non_clickable')
    kb.button(text=f'Сделать ставку: {data.get('min_rate')} ₽',url = f'https://t.me/{data.get("bot_username")}')
    kb.adjust(2,1,1,1,1)
    return kb.as_markup()