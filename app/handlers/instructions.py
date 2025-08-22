"""
Обработчики для инструкций по использованию бота
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.keyboards import tr
from app.utils import safe_edit_message

router = Router()


@router.callback_query(F.data == 'how_to_use')
async def show_instructions(call: CallbackQuery, state: FSMContext):
    """Показать инструкции по использованию"""
    user_id = call.from_user.id

    instruction_text = """
📖 **Как пользоваться ботом:**

1️⃣ **Добавить долг** - создать запись о долге
   • Укажите имя человека
   • Выберите валюту (USD, UZS, EUR)  
   • Введите сумму
   • Укажите дату возврата
   • Выберите направление (дал/взял)
   • Добавьте комментарий (необязательно)

2️⃣ **Мои долги** - посмотреть все долги
   • Список всех активных долгов
   • Нажмите на долг для просмотра деталей
   • Можно редактировать, закрывать или удалять

3️⃣ **Настройки** - управление уведомлениями
   • Установить время напоминаний
   • Бот будет присылать уведомления о долгах

4️⃣ **Очистить все** - удалить все долги

5️⃣ **Смена языка** - переключение между языками

❓ Если возникли вопросы, попробуйте добавить тестовый долг и поэкспериментировать с функциями бота.
"""

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🏠 В меню",
            callback_data='back_main'
        )]
    ])

    await safe_edit_message(call, instruction_text, kb, parse_mode='Markdown')