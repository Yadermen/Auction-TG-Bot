from loguru import logger
from aiogram.filters import CommandObject, Command,StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram import F
from loguru import logger

from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.bot.filters.get_user_info import GetUserInfoFilter
from app.bot.keyboards.markup_kbs import MainKeyboard,del_kbd
from app.db.dao import LotDAO
from app.db.schemas import LotFilterModel
from app.db.database import async_session_maker
from app.db.models import User

from app.config import bot,settings

do_rate_router = Router()

class RateLot(StatesGroup):
    lot_number = State()
    rate = State()
    confirm = State()

@do_rate_router.message(F.text == MainKeyboard.get_user_kb_texts().get('do_rate'))
async def cmd_do_rate(message:Message, state:FSMContext):
    await message.answer('Введите номер лота',reply_markup=del_kbd)
    await state.set_state(RateLot.lot_number)

@do_rate_router.message(F.text, StateFilter(RateLot.lot_number),GetUserInfoFilter())
async def process_lot_num(message:Message, state:FSMContext, user_info:User):
    try:
        async with async_session_maker() as session:
            lot = await LotDAO.find_one_or_none_by_id(message.text, session)
            if not lot:
                await message.answer('Лот с таким номером не найден',reply_markup=MainKeyboard.build_main_kb(user_info.role))
                await state.clear()
                return
            if lot.curren_rate is not None:
                min_rate = lot.curren_rate + lot.rate_step
            else:
                min_rate = lot.price
            await message.answer(f'Теперь введите вашу ставку(Минимальная ставка: **{min_rate}**)\nВводите только числа без разделения пробелами, запятыми и тд(Например 250000)', parse_mode='markdown')
            await state.set_state(RateLot.rate)
            await state.update_data({'lot_number':lot.id})
            await state.update_data({'min_rate':min_rate})
    except Exception as e:
        logger.info(f'Во время поиска лота у юзера{message.from_user.id} произошла ошибка - {str(e)}')
        await message.answer('Произошла не предвиденная ошибка',reply_markup=MainKeyboard.build_main_kb(user_info.role))

@do_rate_router.message(F.text.regexp(r'^\d+$'), StateFilter(RateLot.rate),GetUserInfoFilter())
async def process_rate(message:Message, state:FSMContext, user_info:User):
    try:
        data = await state.get_data()
        min_rate = data.get('min_rate')
        if int(message.text) < int(min_rate):
            await message.answer('Ваша ставка меньше минимальной',reply_markup=MainKeyboard.build_main_kb(user_info.role))
            await state.clear()
            return
        async with async_session_maker() as session:
            lot = await LotDAO.find_one_or_none_by_id(data.get('lot_number'),session)
            lot.curren_rate = int(message.text)
        async with async_session_maker() as session:
            await LotDAO.update(session,
                                filters=LotFilterModel(id=int(data.get('lot_number'))),
                                values=LotFilterModel.model_validate(lot.to_dict()))
        await message.answer('Спасибо за вашу ставку!')
        msg = f'Пользователь {user_info.user_enter_fio}(phone_num:{user_info.phone_number}; tg_id:`{user_info.telegram_id}`)\nсделал ставку в размере {message.text} на лот под номером:{lot.id}'
        await bot.send_message(settings.ADMIN_GROUP_ID, msg, parse_mode='markdown')
    except Exception as e:
        logger.info(f'Во время ввода ставки у юзера {message.from_user.id} произошла ошибка - {str(e)}')
        await message.answer('Произошла не предвиденная ошибка',reply_markup=MainKeyboard.build_main_kb(user_info.role))