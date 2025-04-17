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
from app.db.dao import LotDAO,UserDAO
from app.db.database import async_session_maker
from app.config import bot,settings
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.db.models import User
from app.db.schemas import LotCreateModel, LotFilterModel, TelegramIDModel

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


@create_lot_router.message(F.text == MainKeyboard.get_admin_kb_texts().get('create_lot'))
async def start_create_lot(message: Message, state: FSMContext):
    await message.answer("Введите информацию о лоте:",reply_markup=del_kbd)
    await state.set_state(CreateLot.lot_info)


@create_lot_router.message(F.text, StateFilter(CreateLot.lot_info))
async def set_lot_info(message: Message, state: FSMContext):
    await state.update_data(lot_info=message.html_text)
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
    await message.answer_photo(photo=data.get('main_photo'), caption=msg, reply_markup=lot_confirm(),parse_mode='html')



@create_lot_router.callback_query(LotConfirmCallback.filter())
async def process_confirm_callback(query: CallbackQuery, callback_data: LotConfirmCallback,state:FSMContext):
    match callback_data.action:
        case 'yes':
            try:
                data = await state.get_data()
                async with async_session_maker() as session:
                    lot_data = LotCreateModel(
                        lot_info=data.get('lot_info'),
                        price=data.get('price'),
                        rate_step=data.get('rate_step'),
                        time_in_minutes=data.get('time_in_minutes'),
                        main_photo=data.get('main_photo'),
                        photos_link=data.get('photos_link'),
                        autoteka_link=data.get('autoteka_link'),
                        diagnostik_link=data.get('diagnostik_link'),
                    )
                    await LotDAO.add(session=session, values=lot_data)

                async with async_session_maker() as session:
                    lot = await LotDAO.find_one_or_none(session,filters=LotFilterModel(
                        lot_info=data.get('lot_info'),
                        price=data.get('price'),
                        rate_step=data.get('rate_step'),
                        time_in_minutes=data.get('time_in_minutes'),
                        main_photo=data.get('main_photo'),
                        photos_link=data.get('photos_link'),
                        autoteka_link=data.get('autoteka_link'),
                        diagnostik_link=data.get('diagnostik_link')))
                    lot_id = lot.id
                data.update({'lot_id':lot_id})
                me = await bot.get_me()
                data.update({'bot_username':me.username})
                data.update({'min_rate':lot.price})
                message = await bot.send_photo(chat_id=settings.USER_GROUP_ID,
                                             photo=data.get('main_photo'),
                                             caption=f'Лот: {lot_id}\n'+data.get('lot_info'), 
                                             parse_mode='html',
                                             reply_markup=lot_kb(data))
                asyncio.create_task(process_auction(message, data))
                await query.message.delete()
                await query.message.answer("Лот создан!",reply_markup=MainKeyboard.build_main_kb(User.Role.admin))
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
            auk_message = await bot.send_message(chat_id=settings.USER_GROUP_ID,text='**ВНИМАНИЕ ДО КОНЦА АУКЦИОНА ОСТАЛОСЬ 5 МИНУТ**',parse_mode='markdown')
        if remaining_time <= 0:
            await bot.delete_message(chat_id=settings.USER_GROUP_ID,message_id=auk_message.message_id)
            if lot.current_rate_user_id:
                async with async_session_maker() as session:
                    user_who_won = await UserDAO.find_one_or_none(session,filters=TelegramIDModel(telegram_id=lot.current_rate_user_id))
                    user_link = f"@{user_who_won.username}" if user_who_won.username else f"<a href='https://t.me/{user_who_won.telegram_id}'>пользователь</a>"
                    await bot.send_message(
                        chat_id=settings.ADMIN_GROUP_ID,
                        text=(
                            f"**АУКЦИОН №{lot.id} ЗАВЕРШЕН**\n"
                            f"Победитель: {user_who_won.user_enter_fio}\n"
                            f"Телефон: {user_who_won.phone_number}\n"
                            f"Telegram: {user_link}"
                        ),
                        parse_mode='html'
                    )
            await message.edit_reply_markup(reply_markup=None)
            await message.edit_text(message.md_text + '\n **АУКЦИОН ЗАВЕРШЕН, ВСЕМ СПАСИБО ЗА УЧАСТИЕ**',parse_mode='markdown')
            break

        data.update({'time_in_minutes':remaining_time})
        if lot.curren_rate is not None:
            min_rate = lot.curren_rate + lot.rate_step
        else:
            min_rate = lot.price
        data.update({'min_rate':min_rate})
        try:
            message = await message.edit_reply_markup(reply_markup=lot_kb(data))
        except Exception as e:
            logger.error(f"Ошибка при обновлении клавиатуры: {e}")
            break

        await asyncio.sleep(60)  