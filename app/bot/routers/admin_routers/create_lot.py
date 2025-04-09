import asyncio

from aiogram.filters import Command,StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram import F
from loguru import logger

from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router
from app.bot.keyboards.inlane_kb import lot_confirm,LotConfirmCallback, lot_kb
from app.bot.keyboards.markup_kbs import MainKeyboard,del_kbd
from app.bot.utils.func import generate_lot_confirmation_text
from app.db.dao import LotDAO
from app.db.database import async_session_maker
from app.config import bot,settings
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.db.models import User
from app.db.schemas import LotCreateModel  

create_lot_router = Router()

class CreateLot(StatesGroup):
    lot_info = State()
    price = State()
    rate_step = State()
    time_in_minutes = State()
    main_photo = State()
    photos_link = State()
    autoteka_link = State()
    diagnostik_link = State()
    confirm = State()


@create_lot_router.message(F.text == MainKeyboard.get_admin_kb_texts('create_lot').get())
async def start_create_lot(message: Message, state: FSMContext):
    await message.answer("Введите информацию о лоте:",reply_markup=del_kbd)
    await state.set_state(CreateLot.lot_info)


@create_lot_router.message(F.text, StateFilter(CreateLot.lot_info))
async def set_lot_info(message: Message, state: FSMContext):
    await state.update_data(lot_info=message.md_text)
    await message.answer("Введите цену лота:")
    await state.set_state(CreateLot.price)


@create_lot_router.message(F.text, StateFilter(CreateLot.price))
async def set_price(message: Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer("Введите шаг ставки:")
        await state.set_state(CreateLot.rate_step)
    except ValueError:
        await message.answer("Цена должна быть числом. Попробуйте снова.")


@create_lot_router.message(F.text, StateFilter(CreateLot.rate_step))
async def set_rate_step(message: Message, state: FSMContext):
    try:
        rate_step = float(message.text)
        await state.update_data(rate_step=rate_step)
        await message.answer("Введите время в минутах:")
        await state.set_state(CreateLot.time_in_minutes)
    except ValueError:
        await message.answer("Шаг ставки должен быть числом. Попробуйте снова.")


@create_lot_router.message(F.text, StateFilter(CreateLot.time_in_minutes))
async def set_time(message: Message, state: FSMContext):
    try:
        time_in_minutes = int(message.text)
        await state.update_data(time_in_minutes=time_in_minutes)
        await message.answer("Отправьте главную фотографию в чат:")
        await state.set_state(CreateLot.main_photo)
    except ValueError:
        await message.answer("Время должно быть целым числом. Попробуйте снова.")


@create_lot_router.message(F.photo, StateFilter(CreateLot.main_photo))
async def set_main_photo(message: Message, state: FSMContext):
    await state.update_data(main_photo=message.photo[-1].file_id)
    await message.answer("Отправьте ссылки на дополнительные фото:")
    await state.set_state(CreateLot.photos_link)


@create_lot_router.message(F.text, StateFilter(CreateLot.photos_link))
async def set_photos_link(message: Message, state: FSMContext):
    await state.update_data(photos_link=message.text)
    await message.answer("Отправьте ссылку на отчет Автотека:")
    await state.set_state(CreateLot.autoteka_link)


@create_lot_router.message(F.text, StateFilter(CreateLot.autoteka_link))
async def set_autoteka_link(message: Message, state: FSMContext):
    await state.update_data(autoteka_link=message.text)
    await message.answer("Отправьте ссылку на диагностический отчет:")
    await state.set_state(CreateLot.diagnostik_link)

@create_lot_router.message(F.text,StateFilter(CreateLot.diagnostik_link))
async def set_diagnostik_link(message: Message, state: FSMContext):
    await state.update_data(diagnostik_link=message.text)
    data = await state.get_data()
    msg = await generate_lot_confirmation_text(data)
    await message.answer_photo(photo=data.get('main_photo'), caption=msg, reply_markup=lot_confirm())



@create_lot_router.callback_query(LotConfirmCallback.filter)
async def process_confirm_callback(query: CallbackQuery, callback_data: LotConfirmCallback,state:FSMContext):
    match callback_data.action:
        case 'yes':
            try:
                data = await state.get_data()
                async with async_session_maker() as session:
                    lot_data = LotCreateModel(**data)
                    new_lot = await LotDAO.add(session=session, values=lot_data)
                    data.update({'lot_id':new_lot.id})
                    message = bot.send_photo(chat_id=settings.USER_GROUP_ID,
                                             photo=data.get('main_photo'),
                                             caption=f'Лот: {new_lot.id}\n'+data.get('lot_info'), 
                                             parse_mode='markdown',
                                             reply_markup=lot_kb(data))
                    asyncio.create_task(process_auction(message, data))
            except Exception as e:
                logger.error(f"Ошибка при создании лота: {e}")
                await query.message.answer("Произошла ошибка при создании лота. Попробуйте снова позже.")
            finally:
                await state.clear()
        case 'no':
            await query.message.answer("Понял, отменяю публикацию",reply_markup=MainKeyboard.build_main_kb(User.Role.admin))
            await state.clear()


async def process_auction(message: Message, data: dict):
    """
    Обновляет клавиатуру с оставшимся временем до окончания аукциона.
    """
    remaining_time = data.get('time_in_minutes')
    while True:
        async with async_session_maker() as session:
            lot = await LotDAO.find_one_or_none_by_id(data.get('lot_id'),session)
            data.update({'current_rate':lot.curren_rate})
        remaining_time = remaining_time - 1
        if remaining_time == 5:
            await bot.send_message(chat_id=settings.USER_GROUP_ID,text='**ВНИМАНИЕ ДО КОНЦА АУКЦИОНА ОСТАЛОСЬ 5 МИНУТ**',parse_mode='markdown')
        if remaining_time <= 0:
            await message.edit_reply_markup(reply_markup=None)
            await message.edit_text(message.text + '\n **АУКЦИОН ЗАВЕРШЕН, ВСЕМ СПАСИБО ЗА УЧАСТИЕ**',parse_mode='markdown')
            break

        data.update({'time_in_minutes':remaining_time})
        try:
            await message.edit_reply_markup(reply_markup=lot_kb(data))
        except Exception as e:
            logger.error(f"Ошибка при обновлении клавиатуры: {e}")
            break

        await asyncio.sleep(60)  