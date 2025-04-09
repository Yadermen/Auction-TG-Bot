from typing import Dict
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from loguru import logger

from app.db.models import User

del_kbd = ReplyKeyboardRemove()

def back_button():
    kb = ReplyKeyboardBuilder()
    kb.button(text="Назад")
    return kb.as_markup(resize_keyboard=True)


def request_contact_kb():
    kb = ReplyKeyboardBuilder()
    kb.button(text="📞 Поделиться номером", request_contact=True)
    return kb.as_markup(resize_keyboard=True)


class MainKeyboard:
    __user_kb_texts_dict_ru = {
        'do_rate':'Сделать ставку'
    }

    __admin_kb_text_dict_ru = {
        'create_lot':'Создать лот'
    }
    
    @staticmethod
    def get_user_kb_texts(key = None) -> Dict[str, str] | None:
        """
        'do_rate'
        """
        if key is not None:
            return MainKeyboard.__user_kb_texts_dict_ru.get(key)
        return MainKeyboard.__user_kb_texts_dict_ru

    @staticmethod
    def get_admin_kb_texts(key = None) -> Dict[str, str]:
        """
        'create_lot'
        """
        if key is not None:
            return MainKeyboard.__admin_kb_text_dict_ru.get(key)
        return MainKeyboard.__admin_kb_text_dict_ru

    @staticmethod
    def build_main_kb(user_role: User.Role) -> ReplyKeyboardMarkup:
        kb = ReplyKeyboardBuilder()

        for val in MainKeyboard.get_user_kb_texts().values():
            kb.button(text=val)
        if user_role == User.Role.admin:
            for val in MainKeyboard.get_admin_kb_texts().values():
                kb.button(text=val)
        kb.adjust(
            len(MainKeyboard.get_user_kb_texts()),
            len(MainKeyboard.get_admin_kb_texts()),
        )

        return kb.as_markup(resize_keyboard=True)
