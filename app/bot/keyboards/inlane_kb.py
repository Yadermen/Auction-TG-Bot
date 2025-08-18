from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
import re

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


class LotConfirmCallback(CallbackData, prefix="lot_confirm"):
    action: str


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
            action="no",
        ).pack()
    )
    kb.adjust(2)
    return kb.as_markup()


def is_valid_url(url: str) -> bool:
    if not url or len(url.strip()) <= 1:
        return False

    url_pattern = re.compile(
        r'^https?://'
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
        r'localhost|'
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
        r'(?::\d+)?'
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)

    return url_pattern.match(url.strip()) is not None


def lot_kb(data: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    photos_link = data.get('photos_link')
    if is_valid_url(photos_link):
        kb.button(text='📸 Фото', url=photos_link)

    autoteka_link = data.get('autoteka_link')
    if is_valid_url(autoteka_link):
        kb.button(text='🔍 Автотека', url=autoteka_link)

    time_left = minutes_to_hours_and_minutes(data.get('time_in_minutes', 0))
    kb.button(
        text=f'⏰ До конца: {time_left}',
        callback_data='time_info'
    )

    current_rate = data.get('current_rate')
    if current_rate:
        kb.button(
            text=f'💰 Текущая ставка: {current_rate} ₽',
            callback_data='current_bid_info'
        )
    else:
        kb.button(
            text='💰 Ставок пока нет',
            callback_data='no_bids_info'
        )

    min_rate = data.get('min_rate', 0)
    bot_username = data.get('bot_username')
    if bot_username:
        kb.button(
            text=f'🚀 Сделать ставку: {min_rate} ₽',
            url=f'https://t.me/{bot_username}?start=bid_{data.get("lot_id", "")}'
        )

    photos_count = 1 if is_valid_url(photos_link) else 0
    autoteka_count = 1 if is_valid_url(autoteka_link) else 0

    if photos_count + autoteka_count == 2:
        kb.adjust(2, 1, 1, 1)
    elif photos_count + autoteka_count == 1:
        kb.adjust(1, 1, 1, 1)
    else:
        kb.adjust(1, 1, 1)

    return kb.as_markup()


def completed_auction_kb(data: dict) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()

    photos_link = data.get('photos_link')
    if is_valid_url(photos_link):
        kb.button(text='📸 Фото', url=photos_link)

    autoteka_link = data.get('autoteka_link')
    if is_valid_url(autoteka_link):
        kb.button(text='🔍 Автотека', url=autoteka_link)


    kb.adjust(3)
    return kb.as_markup()


class BidCallback(CallbackData, prefix="bid"):
    action: str
    lot_id: int
    amount: float = None


def bid_confirmation_kb(lot_id: int, amount: float) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Подтвердить ставку",
        callback_data=BidCallback(
            action="confirm",
            lot_id=lot_id,
            amount=amount
        ).pack()
    )
    kb.button(
        text="❌ Отменить",
        callback_data=BidCallback(
            action="cancel",
            lot_id=lot_id
        ).pack()
    )
    kb.adjust(2)
    return kb.as_markup()
