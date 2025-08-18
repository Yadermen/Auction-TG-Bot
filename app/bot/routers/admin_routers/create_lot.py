import asyncio
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List

from aiogram.filters import Command, StateFilter
from aiogram.filters.callback_data import CallbackData
from aiogram import F
from loguru import logger

from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router
from app.bot.keyboards.inlane_kb import lot_confirm, LotConfirmCallback, lot_kb, completed_auction_kb
from app.bot.keyboards.markup_kbs import MainKeyboard, del_kbd
from app.bot.utils.func import generate_lot_confirmation_text
from app.db.dao import LotDAO, UserDAO
from app.db.database import async_session_maker
from app.config import bot, settings
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from app.db.models import User
from app.db.schemas import LotCreateModel, LotFilterModel, TelegramIDModel

create_lot_router = Router()

media_groups: Dict[str, List[Message]] = defaultdict(list)
media_group_timers: Dict[str, asyncio.Task] = {}


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


async def process_media_group(media_group_id: str, state: FSMContext):
    await asyncio.sleep(1)

    messages = media_groups.get(media_group_id, [])
    if not messages:
        return

    photo_ids = []
    for msg in messages:
        if msg.photo:
            photo_ids.append(msg.photo[-1].file_id)

    if photo_ids:
        await state.update_data(
            main_photo=photo_ids[0],
            additional_photos=photo_ids[1:] if len(photo_ids) > 1 else []
        )

        first_message = messages[0]
        if len(photo_ids) == 1:
            await first_message.answer(
                "✅ Главное фото загружено!\nОтправьте ссылки на дополнительные фото (или напишите 'нет' если их нет):")
        else:
            await first_message.answer(
                f"✅ Загружено {len(photo_ids)} фотографий!\nПервое фото будет главным, остальные - дополнительными.\nОтправьте ссылки на дополнительные фото (или напишите 'нет' если их нет):")

        await state.set_state(CreateLot.photos_link)

    media_groups.pop(media_group_id, None)
    media_group_timers.pop(media_group_id, None)


@create_lot_router.message(F.text == MainKeyboard.get_admin_kb_texts().get('create_lot'))
async def start_create_lot(message: Message, state: FSMContext):
    await message.answer("Введите информацию о лоте:", reply_markup=del_kbd)
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
        if price <= 0:
            await message.answer("❌ Цена должна быть положительным числом. Попробуйте снова.")
            return
        await state.update_data(price=price)
        await message.answer("Введите шаг ставки:")
        await state.set_state(CreateLot.rate_step)
    except ValueError:
        await message.answer("❌ Цена должна быть числом. Попробуйте снова.")


@create_lot_router.message(F.text, StateFilter(CreateLot.rate_step))
async def set_rate_step(message: Message, state: FSMContext):
    try:
        rate_step = float(message.text)
        if rate_step <= 0:
            await message.answer("❌ Шаг ставки должен быть положительным числом. Попробуйте снова.")
            return
        await state.update_data(rate_step=rate_step)
        await message.answer("Введите время в минутах:")
        await state.set_state(CreateLot.time_in_minutes)
    except ValueError:
        await message.answer("❌ Шаг ставки должен быть числом. Попробуйте снова.")


@create_lot_router.message(F.text, StateFilter(CreateLot.time_in_minutes))
async def set_time(message: Message, state: FSMContext):
    try:
        time_in_minutes = int(message.text)
        if time_in_minutes <= 0:
            await message.answer("❌ Время должно быть положительным числом. Попробуйте снова.")
            return
        if time_in_minutes > 1440:
            await message.answer("❌ Время не может превышать 1440 минут (24 часа). Попробуйте снова.")
            return
        await state.update_data(time_in_minutes=time_in_minutes)
        await message.answer("Отправьте главную фотографию (или несколько фотографий) в чат:")
        await state.set_state(CreateLot.main_photo)
    except ValueError:
        await message.answer("❌ Время должно быть целым числом. Попробуйте снова.")


@create_lot_router.message(F.photo, StateFilter(CreateLot.main_photo))
async def set_main_photo(message: Message, state: FSMContext):
    if message.media_group_id:
        media_group_id = message.media_group_id
        media_groups[media_group_id].append(message)

        if media_group_id in media_group_timers:
            media_group_timers[media_group_id].cancel()

        media_group_timers[media_group_id] = asyncio.create_task(
            process_media_group(media_group_id, state)
        )
    else:
        await state.update_data(
            main_photo=message.photo[-1].file_id,
            additional_photos=[]
        )
        await message.answer(
            "✅ Главное фото загружено!\nОтправьте ссылки на дополнительные фото (или напишите 'нет' если их нет):")
        await state.set_state(CreateLot.photos_link)


@create_lot_router.message(F.text, StateFilter(CreateLot.photos_link))
async def set_photos_link(message: Message, state: FSMContext):
    photos_link = message.text.strip()
    if photos_link.lower() in ['нет', 'отсутствует', '-', 'no']:
        photos_link = ""
    await state.update_data(photos_link=photos_link)
    await message.answer("Отправьте ссылку на отчет Автотека (или напишите 'нет' если нет):")
    await state.set_state(CreateLot.autoteka_link)


@create_lot_router.message(F.text, StateFilter(CreateLot.autoteka_link))
async def set_autoteka_link(message: Message, state: FSMContext):
    autoteka_link = message.text.strip()
    if autoteka_link.lower() in ['нет', 'отсутствует', '-', 'no']:
        autoteka_link = ''
    await state.update_data(autoteka_link=autoteka_link, diagnostik_link="")

    data = await state.get_data()
    msg = await generate_lot_confirmation_text(data)

    await message.answer_photo(
        photo=data.get('main_photo'),
        caption=msg,
        reply_markup=lot_confirm(),
        parse_mode='html'
    )

    additional_photos = data.get('additional_photos', [])
    if additional_photos:
        await message.answer(f"📷 Дополнительно будет загружено {len(additional_photos)} фотографий")


@create_lot_router.callback_query(LotConfirmCallback.filter())
async def process_confirm_callback(query: CallbackQuery, callback_data: LotConfirmCallback, state: FSMContext):
    match callback_data.action:
        case 'yes':
            try:
                data = await state.get_data()

                try:
                    await bot.get_chat(settings.USER_GROUP_ID)
                    await bot.get_chat(settings.ADMIN_GROUP_ID)
                except Exception as e:
                    logger.error(f"Группы недоступны: {e}")
                    await query.message.answer(
                        "❌ Ошибка: Группы для аукциона недоступны. "
                        "Проверьте настройки групп и права бота."
                    )
                    return

                async with async_session_maker() as session:
                    additional_photos = data.get('additional_photos', [])
                    additional_photos_str = ','.join(additional_photos) if additional_photos else ''

                    lot_data = LotCreateModel(
                        lot_info=data.get('lot_info'),
                        price=data.get('price'),
                        rate_step=data.get('rate_step'),
                        time_in_minutes=data.get('time_in_minutes'),
                        main_photo=data.get('main_photo'),
                        additional_photos=additional_photos_str,
                        photos_link=data.get('photos_link'),
                        autoteka_link=data.get('autoteka_link'),
                        diagnostik_link=data.get('diagnostik_link'),
                        is_active=True
                    )
                    await LotDAO.add(session=session, values=lot_data)

                async with async_session_maker() as session:
                    lot = await LotDAO.find_one_or_none(session, filters=LotFilterModel(
                        lot_info=data.get('lot_info'),
                        price=data.get('price'),
                        rate_step=data.get('rate_step'),
                        time_in_minutes=data.get('time_in_minutes'),
                        main_photo=data.get('main_photo'),
                        photos_link=data.get('photos_link'),
                        autoteka_link=data.get('autoteka_link'),
                        diagnostik_link=data.get('diagnostik_link')
                    ))
                    lot_id = lot.id

                me = await bot.get_me()
                data.update({
                    'lot_id': lot_id,
                    'bot_username': me.username,
                    'min_rate': lot.price,
                    'current_rate': None
                })

                try:
                    main_photo = data.get('main_photo')
                    additional_photos = data.get('additional_photos', [])
                    all_photos = [main_photo] + additional_photos

                    if len(all_photos) == 1:
                        photo_message = await bot.send_photo(
                            chat_id=settings.USER_GROUP_ID,
                            photo=main_photo,
                            caption=f'🚗 **Лот №{lot_id}**',
                            parse_mode='markdown'
                        )
                    else:
                        from aiogram.types import InputMediaPhoto
                        media_group = []

                        media_group.append(InputMediaPhoto(
                            media=all_photos[0],
                            caption=f'🚗 **Лот №{lot_id}**',
                            parse_mode='markdown'
                        ))

                        for photo_id in all_photos[1:9]:
                            media_group.append(InputMediaPhoto(media=photo_id))

                        media_messages = await bot.send_media_group(
                            chat_id=settings.USER_GROUP_ID,
                            media=media_group
                        )
                        photo_message = media_messages[0]

                except Exception as e:
                    logger.error(f"Ошибка при отправке фото: {e}")
                    if "message is too long" in str(e):
                        await query.message.answer("❌ Ошибка: Слишком длинное описание лота")
                    elif "photo not found" in str(e):
                        await query.message.answer("❌ Ошибка: Фото недоступно")
                    else:
                        await query.message.answer(f"❌ Ошибка при создании лота: {e}")
                    return

                try:
                    description_message = await bot.send_message(
                        chat_id=settings.USER_GROUP_ID,
                        text=f'**Лот №{lot_id}**\n\n{data.get("lot_info")}',
                        reply_markup=lot_kb(data),
                        parse_mode='markdown'
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке описания: {e}")
                    try:
                        await bot.delete_message(settings.USER_GROUP_ID, photo_message.message_id)
                    except:
                        pass

                    if "message is too long" in str(e):
                        await query.message.answer("❌ Ошибка: Слишком длинное описание лота")
                    else:
                        await query.message.answer(f"❌ Ошибка при создании описания лота: {e}")
                    return

                asyncio.create_task(
                    process_auction(description_message, data, photo_message.message_id)
                )

                await query.message.delete()
                await query.message.answer(
                    f"✅ Лот №{lot_id} создан и опубликован!",
                    reply_markup=MainKeyboard.build_main_kb(User.Role.admin)
                )

            except Exception as e:
                logger.error(f"Критическая ошибка при создании лота: {e}")
                await query.message.answer(
                    "❌ Произошла критическая ошибка при создании лота. "
                    "Обратитесь к разработчику."
                )
            finally:
                await state.clear()

        case 'no':
            await query.message.answer(
                "❌ Создание лота отменено",
                reply_markup=MainKeyboard.build_main_kb(User.Role.admin)
            )
            await state.clear()


import asyncio
from datetime import datetime

auction_update_events = {}


async def process_auction(message: Message, data: dict, photo_message_id: int):
    remaining_time = data.get('time_in_minutes')
    last_bid_time = None
    five_minutes_warning_sent = False
    lot_id = data.get('lot_id')

    update_event = asyncio.Event()
    auction_update_events[lot_id] = update_event

    logger.info(f"Запуск аукциона для лота {lot_id}, время: {remaining_time} минут")

    try:
        while True:
            try:
                logger.debug(f"Лот {lot_id}: Осталось времени {remaining_time} минут")

                async with async_session_maker() as session:
                    lot = await LotDAO.find_one_or_none_by_id(data.get('lot_id'), session)
                    if not lot:
                        logger.error(f"Лот {data.get('lot_id')} не найден в БД - завершаем аукцион")
                        break

                    data.update({'current_rate': lot.curren_rate})
                    logger.debug(f"Лот {lot_id}: Текущая ставка {lot.curren_rate}")

                bid_updated = False
                if lot.curren_rate and lot.curren_rate != data.get('last_known_rate'):
                    data.update({'last_known_rate': lot.curren_rate})
                    last_bid_time = datetime.now()
                    bid_updated = True
                    logger.info(f"Лот {lot_id}: Новая ставка {lot.curren_rate}, время ставки: {last_bid_time}")

                    if remaining_time < 30:
                        old_time = remaining_time
                        remaining_time = 30
                        logger.info(f"Лот {lot_id}: Автопродление с {old_time} до {remaining_time} минут")
                        try:
                            await bot.send_message(
                                chat_id=settings.USER_GROUP_ID,
                                text=f"⏰ **ВНИМАНИЕ!** Аукцион по лоту №{lot_id} автоматически продлен на 30 минут из-за новой ставки!",
                                parse_mode='markdown'
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при отправке уведомления о продлении: {e}")

                remaining_time = remaining_time - 1
                logger.debug(f"Лот {lot_id}: После уменьшения осталось {remaining_time} минут")

                if remaining_time == 5 and not five_minutes_warning_sent:
                    logger.info(f"Лот {lot_id}: Отправляем предупреждение за 5 минут")
                    try:
                        await bot.send_message(
                            chat_id=settings.USER_GROUP_ID,
                            text=f'⚠️ **ВНИМАНИЕ! До окончания аукциона по лоту №{lot_id} осталось 5 минут!**',
                            parse_mode='markdown'
                        )
                        five_minutes_warning_sent = True
                    except Exception as e:
                        logger.error(f"Ошибка при отправке предупреждения: {e}")

                if remaining_time <= 0:
                    logger.info(f"Лот {lot_id}: Время истекло, завершаем аукцион")
                    try:
                        if lot.current_rate_user_id:
                            logger.info(f"Лот {lot_id}: Есть победитель {lot.current_rate_user_id}")
                            async with async_session_maker() as session:
                                user_who_won = await UserDAO.find_one_or_none(
                                    session,
                                    filters=TelegramIDModel(telegram_id=lot.current_rate_user_id)
                                )

                                if user_who_won:
                                    user_link = f"@{user_who_won.username}" if user_who_won.username else f"<a href='https://t.me/{user_who_won.telegram_id}'>пользователь</a>"

                                    await bot.send_message(
                                        chat_id=settings.ADMIN_GROUP_ID,
                                        text=(
                                            f"🏆 **АУКЦИОН №{lot.id} ЗАВЕРШЕН**\n\n"
                                            f"👤 Победитель: {user_who_won.user_enter_fio}\n"
                                            f"🚗 Лот: №{lot.id}\n"
                                            f"💰 Финальная ставка: {lot.curren_rate} ₽\n"
                                            f"📞 Телефон: {user_who_won.phone_number}\n"
                                            f"📱 Telegram: {user_link}"
                                        ),
                                        parse_mode='html'
                                    )

                                    await bot.send_message(
                                        chat_id=settings.USER_GROUP_ID,
                                        text=(
                                            f"🏁 **АУКЦИОН №{lot.id} ЗАВЕРШЕН!**\n\n"
                                            f"🎉 Всем спасибо за участие!\n"
                                            f"💰 Ставка победителя: **{lot.curren_rate} ₽**"
                                        ),
                                        parse_mode='markdown'
                                    )
                                else:
                                    logger.warning(f"Лот {lot_id}: Пользователь-победитель не найден в БД")
                        else:
                            logger.info(f"Лот {lot_id}: Аукцион завершен без ставок")
                            await bot.send_message(
                                chat_id=settings.USER_GROUP_ID,
                                text=(
                                    f"🏁 **АУКЦИОН №{lot.id} ЗАВЕРШЕН!**\n\n"
                                    f"😔 К сожалению, ставок не было.\n"
                                    f"🙏 Всем спасибо за внимание!"
                                ),
                                parse_mode='markdown'
                            )

                        async with async_session_maker() as session:
                            await LotDAO.update(
                                session,
                                filters=LotFilterModel(id=lot.id),
                                values={'is_active': False}
                            )
                        logger.info(f"Лот {lot_id}: Лот деактивирован в БД")

                        try:
                            await message.edit_reply_markup(reply_markup=completed_auction_kb(data))
                            await message.edit_text(
                                text=message.text + '\n\n🏁 **АУКЦИОН ЗАВЕРШЕН**',
                                parse_mode='markdown',
                                reply_markup=completed_auction_kb(data)
                            )
                            logger.info(f"Лот {lot_id}: Сообщение обновлено")
                        except Exception as e:
                            logger.error(f"Ошибка при обновлении сообщения завершенного аукциона: {e}")

                    except Exception as e:
                        logger.error(f"Ошибка при завершении аукциона {lot_id}: {e}")

                    logger.info(f"Лот {lot_id}: Аукцион завершен, выходим из цикла")
                    break

                data.update({'time_in_minutes': remaining_time})
                if lot.curren_rate is not None:
                    min_rate = lot.curren_rate + lot.rate_step
                else:
                    min_rate = lot.price
                data.update({'min_rate': min_rate})

                try:
                    await message.edit_reply_markup(reply_markup=lot_kb(data))
                    logger.debug(f"Лот {lot_id}: Клавиатура обновлена")
                except Exception as e:
                    logger.error(f"Ошибка при обновлении клавиатуры лота {lot_id}: {e}")

                try:
                    await asyncio.wait_for(update_event.wait(), timeout=60.0)
                    update_event.clear()
                    logger.info(f"Лот {lot_id}: Получен сигнал немедленного обновления")
                    remaining_time += 1
                except asyncio.TimeoutError:
                    pass

            except Exception as e:
                logger.error(f"Критическая ошибка в цикле аукциона {lot_id}: {e}")
                remaining_time -= 1
                if remaining_time <= 0:
                    logger.error(f"Лот {lot_id}: Принудительное завершение из-за ошибок")
                    break
                await asyncio.sleep(60)

    finally:
        auction_update_events.pop(lot_id, None)


def trigger_auction_update(lot_id: int):
    if lot_id in auction_update_events:
        auction_update_events[lot_id].set()
        logger.info(f"Лот {lot_id}: Запущено немедленное обновление")


async def handle_bid(callback_query, lot_id: int, bid_amount: float):
    try:
        async with async_session_maker() as session:
            pass

        trigger_auction_update(lot_id)

        await callback_query.answer("Ставка принята!")

    except Exception as e:
        logger.error(f"Ошибка при обработке ставки: {e}")
        await callback_query.answer("Произошла ошибка при обработке ставки")