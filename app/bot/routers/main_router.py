from aiogram.filters import CommandObject, CommandStart, StateFilter,Command
from aiogram.types import Message
from aiogram.dispatcher.router import Router
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram import F
from aiogram.enums import ParseMode

from loguru import logger

from app.bot.keyboards.inlane_kb import verified_user
from app.bot.keyboards.markup_kbs import MainKeyboard, request_contact_kb,del_kbd
from app.bot.midlewares.is_admin import CheckIsAdmin
from app.bot.midlewares.white_list import VerificationMiddleware
from app.bot.utils.func import escape_markdown
from app.config import admins,bot
from app.db.dao import UserDAO
from app.db.models import User
from app.db.schemas import TelegramIDModel, UserModel
from app.db.database import async_session_maker
from app.bot.routers.admin_routers.user_contol import user_control_router
from app.bot.routers.admin_routers.create_lot import create_lot_router
from app.bot.routers.user_routers.do_rate import do_rate_router

main_router = Router()

user_control_router.message.middleware(CheckIsAdmin())
create_lot_router.message.middleware(CheckIsAdmin())
main_router.include_router(user_control_router)
main_router.include_router(create_lot_router)

do_rate_router.message.middleware(VerificationMiddleware())
main_router.include_router(do_rate_router)


class Registration(StatesGroup):
    phone_number = State()
    fio = State()

@main_router.message(CommandStart())
async def cmd_start(message: Message,state:FSMContext):
    try:
        async with async_session_maker() as session:
            user_id = message.from_user.id
            user_info = await UserDAO.find_one_or_none(
                session=session, filters=TelegramIDModel(telegram_id=user_id)
            )

            if user_info:
                if user_id in admins:
                    values = UserModel(
                        telegram_id=user_id,
                        username=message.from_user.username,
                        first_name=message.from_user.first_name,
                        last_name=message.from_user.last_name,
                        phone_number=user_info.phone_number,
                        user_enter_fio=user_info.user_enter_fio,
                        verification_status=User.VerifocationStatus.verifed,
                        role=User.Role.admin,
                    )
                    await UserDAO.update(session,filters=TelegramIDModel(telegram_id=user_id),values=values)
                    await message.answer(
                        "Привет администрации", reply_markup=MainKeyboard.build_main_kb(user_role=values.role)
                    )
                    return
                match user_info.verification_status:
                    case User.VerifocationStatus.non_verifed:
                        msg = "Ваш аккаунт еще не проверен. Ожидайте, пока администратор проверит ваш аккаунт."
                        await message.answer(msg)
                        return
                    case User.VerifocationStatus.verifed:
                        msg = "Мы уже проверили ваш аккаунт. Вы можете начать пользоваться ботом."
                        await message.answer(
                            msg, reply_markup=MainKeyboard.build_main_kb(user_role=user_info.role)
                        )
                        return
                    case User.VerifocationStatus.banned:
                        admin_link_msg = ""
                        admins_list: list[User] = await UserDAO.find_all_admins(session)
                        for admin in admins_list:
                            admin_link_msg = (
                                f"@{admin.username}\n"
                                if admin.username
                                else f'<a href="tg://user?id={admin.telegram_id}">администрация</a>\n'
                            )
                        msg = (
                            "Ваш аккаунт заблокирован. Если хотите обжалобить свяжитесь с нами:\n"
                            + admin_link_msg
                        )
                        await message.answer(msg)
                        return

            if user_id in admins:
                values = UserModel(
                    telegram_id=user_id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    phone_number=None,
                    user_enter_fio=None,
                    verification_status=User.VerifocationStatus.verifed,
                    role=User.Role.admin,
                )
                await UserDAO.add(session=session, values=values)
                await message.answer(
                    "Привет администрации", reply_markup=MainKeyboard.build_main_kb(user_role=values.role)
                )
                return
            await message.answer('Для того чтобы пользоваться сделать ставку, поделитесь своим номером телефона',reply_markup=request_contact_kb())
            await state.set_state(Registration.phone_number)
    except Exception as e:
        logger.error(
            f"Ошибка при выполнении команды /start для пользователя {message.from_user.id}: {e}"
        )
        await message.answer(
            "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже."
        )

@main_router.message(F.contact, StateFilter(Registration.phone_number))
async def handle_contact(message: Message, state: FSMContext):
    """
    Обработчик для получения контакта и записи номера телефона в state.
    """
    try:
        phone_number = message.contact.phone_number
        await state.update_data(phone_number=phone_number)
        logger.info(f"Номер телефона {phone_number} записан в state для пользователя {message.from_user.id}")
        await message.answer('Отлично! Осталось совсем немного! \nТеперь пожалуйста напишите ваше фио как в паспорте',reply_markup=del_kbd)
        await state.set_state(Registration.fio)
    except Exception as e:
        logger.error(f"Ошибка при обработке контакта для пользователя {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже.")


@main_router.message(F.text, StateFilter(Registration.fio))
async def handle_fio(message:Message, state:FSMContext):
    try:
        fio = message.text
        data = await state.get_data()
        async with async_session_maker() as session:
            admins = await UserDAO.find_all_admins(session)
        async with async_session_maker() as session:
            user = UserModel(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    phone_number=data.get('phone_number'),
                    user_enter_fio=fio,
                    verification_status=User.VerifocationStatus.non_verifed,
                    role=User.Role.user,
                )
            await UserDAO.add(session=session,
                              values=user)
        msg_for_admins = (
            f"Новый пользователь:\n"
            f"Имя в тг: {message.from_user.first_name or 'Не указано'}\n"
            f"telegram_id: {message.from_user.id}\n"
            f"Номер телефона: {data.get('phone_number') or 'Не указано'}\n"
            f"Указанное пользователем фио: {fio or 'Не указано'}"
        )
        for admin in admins:
            await bot.send_message(
                admin.telegram_id,
                msg_for_admins,
                reply_markup=verified_user(user.telegram_id)
            )        
        await message.answer(f'Приятно познакомиться, {fio}!\nОжидайте проверки вашего профиля администрацией, после чего вы сможете делать ставки')
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при добавлении пользователя {message.from_user.id}: {e}")
        await message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже.")


# @main_router.message(Command("chatid"), F.chat.type.in_({"group", "supergroup"}))
# async def get_chat_id(message: Message):
#     """Returns current chat ID when called from a group"""
#     chat_info = await message.bot.get_chat(message.chat.id)
#     text = (
#         f"📢 Информация о чате:\n\n"
#         f"👥 Название: {chat_info.title}\n"
#         f"🆔 ID: {chat_info.id}"
#     )
    
#     await message.answer(
#         text=text,
#     )