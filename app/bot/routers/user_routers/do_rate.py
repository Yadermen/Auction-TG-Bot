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
from app.bot.routers.admin_routers.create_lot import trigger_auction_update
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
            if not lot.is_active:
                await message.answer('Лот уже не активен',reply_markup=MainKeyboard.build_main_kb(user_info.role))
                await state.clear()
                return
            if lot.curren_rate is not None:
                min_rate = lot.curren_rate + lot.rate_step
            else:
                min_rate = lot.price
            await message.answer(f'Теперь введите вашу ставку(Минимальная ставка: **{min_rate}**)\nВводите только числа без разделения пробелами, запятыми и тд(Например 250000)', parse_mode='markdown')
            await state.set_state(RateLot.rate)
            await state.update_data({'lot_number':lot.id})
            await state.update_data({'user_fio':user_info.user_enter_fio})
            await state.update_data({'user_phone':user_info.phone_number})
            await state.update_data({'user_tg_id':user_info.telegram_id})
    except Exception as e:
        logger.info(f'Во время поиска лота у юзера {message.from_user.id} произошла ошибка - {str(e)}')
        await message.answer('Произошла не предвиденная ошибка',reply_markup=MainKeyboard.build_main_kb(user_info.role))


@do_rate_router.message(F.text.regexp(r'^\d+$'), StateFilter(RateLot.rate), GetUserInfoFilter())
async def process_rate(message: Message, state: FSMContext, user_info: User):
    try:
        data = await state.get_data()
        lot_id = int(data.get('lot_number'))
        new_rate = int(message.text)

        async with async_session_maker() as session:
            lot = await LotDAO.find_one_or_none_by_id(lot_id, session)

            if lot.curren_rate is not None:
                min_rate = lot.curren_rate + lot.rate_step
            else:
                min_rate = lot.price

            if new_rate < min_rate:
                await message.answer('Ваша ставка меньше минимальной',
                                     reply_markup=MainKeyboard.build_main_kb(user_info.role))
                await state.clear()
                return


            previous_leader_id = lot.current_rate_user_id
            previous_rate = lot.curren_rate
            rate_step = lot.rate_step

            await LotDAO.update(session,
                                filters=LotFilterModel(id=lot_id),
                                values=LotFilterModel(
                                    curren_rate=new_rate,
                                    current_rate_user_id=user_info.telegram_id
                                ))

        await message.answer('Спасибо за вашу ставку!', reply_markup=MainKeyboard.build_main_kb(user_info.role))

        msg = f'Пользователь {user_info.user_enter_fio} (phone_num: {user_info.phone_number}; tg_id:`{user_info.telegram_id}`)\nсделал ставку в размере {message.text} на лот под номером: {lot_id}'
        await bot.send_message(settings.ADMIN_GROUP_ID, msg, parse_mode='markdown')
        trigger_auction_update(lot_id)

        if previous_leader_id and previous_leader_id != user_info.telegram_id:
            try:
                outbid_msg = (
                    f"🔥 Ваша ставка перебита!\n\n"
                    f"📦 Лот №{lot_id}\n"
                    f"💰 Ваша ставка: {previous_rate:,}₽\n"
                    f"💰 Новая ставка: {new_rate:,}₽\n"
                    f"📈 Минимальная следующая ставка: {new_rate + rate_step:,}₽\n\n"
                    f"⚡️ Сделайте новую ставку, чтобы остаться в игре!"
                )

                await bot.send_message(previous_leader_id, outbid_msg)
                logger.info(f'Уведомление о перебитой ставке отправлено пользователю {previous_leader_id}')

            except Exception as notify_error:
                logger.error(f'Ошибка при отправке уведомления пользователю {previous_leader_id}: {str(notify_error)}')

        await state.clear()

    except Exception as e:
        logger.info(f'Во время ввода ставки у юзера {message.from_user.id} произошла ошибка - {str(e)}')
        await message.answer('Произошла не предвиденная ошибка',
                             reply_markup=MainKeyboard.build_main_kb(user_info.role))
        await state.clear()