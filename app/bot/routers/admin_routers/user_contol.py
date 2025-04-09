from aiogram.filters import CommandObject, Command
from aiogram.filters.callback_data import CallbackData
from aiogram import F
from loguru import logger

from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.router import Router
from app.bot.keyboards.inlane_kb import VerifedCallback
from app.db.models import User
from app.db.schemas import UserFilterModel,TelegramIDModel
from app.db.dao import UserDAO
from app.bot.keyboards.markup_kbs import MainKeyboard
from app.db.database import async_session_maker
from app.bot.utils.func import is_valid_telegram_id,split_message

user_control_router = Router()
@user_control_router.message(Command("unban"))
async def cmd_unban_user(message: Message, command: CommandObject):
    try:
        user_id: str = command.args
        if not user_id:
            await message.answer(
                "После комманды /unban я ожидаю получить id пользователя в телеграмме"
            )
        elif not is_valid_telegram_id(user_id):
            await message.answer("Не верный формат ввода")
        else:
            async with async_session_maker() as session:
                user: User = await UserDAO.find_one_or_none(session, TelegramIDModel(telegram_id=user_id))
                if not user:
                    await message.answer("Пользователь с таким id не найден")
                    return
                user.verification_status = User.VerifocationStatus.verifed
                await UserDAO.update(
                    session=session,
                    filters=TelegramIDModel(telegram_id=user_id),
                    values=UserFilterModel.model_validate(user.to_dict()),
                )
            await message.answer(f"Пользователь разблокирован")
            await message.bot.send_message(
                user_id,
                f"Поздравляем вас разблокировали!! Вы можете свободно пользоваться ботом",
                reply_markup=MainKeyboard.build_main_kb(user.role),
            )
    except Exception as e:
        logger.error(f"Произошла ошибка при выполнении комманды /unban - {e}")
        await message.answer(f"Произошла ошибка при выполнении комманды /unban - {e}")

@user_control_router.message(Command("ban"))
async def cmd_unban_user(message: Message, command: CommandObject, session, **kwargs):
    try:
        user_id: str = command.args
        if not user_id:
            await message.answer(
                "После комманды /ban я ожидаю получить id пользователя в телеграмме"
            )
        elif not is_valid_telegram_id(user_id):
            await message.answer("Не верный формат ввода")
        else:
            async with async_session_maker() as session:
                user: User = await UserDAO.find_one_or_none(session, TelegramIDModel(telegram_id=user_id))
                if not user:
                    await message.answer("Пользователь с таким id не найден")
                    return
                user.verification_status = User.VerifocationStatus.banned
                await UserDAO.update(
                    session=session,
                    filters=TelegramIDModel(telegram_id=user_id),
                    values=UserFilterModel.model_validate(user.to_dict()),
                )
            await message.answer(f"Пользователь заблокирован")
            await message.bot.send_message(
                user_id,
                f"К сожалению администрация заблокировала вас",
            )
    except Exception as e:
        logger.error(f"Произошла ошибка при выполнении комманды /ban - {e}")
        await message.answer(f"Произошла ошибка при выполнении комманды /ban - {e}")


@user_control_router.message(F.text == "Список забаненных юзеров")
async def get_banned_user_list(message: Message):
    try:
        async with async_session_maker as session:
            banned_users: list[User] = await UserDAO.find_all(session,UserFilterModel(verification_status=User.VerifocationStatus.banned))

        if not banned_users:
            await message.answer("Список заблокированных пользователей пуст.")
            return

        msg = "🔒 Заблокированные пользователи:\n"
        for user in banned_users:
            username = f"@{user.username}" if user.username else "Без имени"
            msg += f"👤 {username} (ID: {user.telegram_id})\n"
        answer = split_message(msg=msg, with_photo=False)
        for i in answer:
            await message.answer(i)
    except Exception as e:
        logger.error(f"Ошибка при получении списка юзеров - {e}")

@user_control_router.message(F.text == "Список пользователей")
async def get_banned_user_list(message: Message):
    try:
        async with async_session_maker() as session:
            users: list[User] = await UserDAO.find_all(session,UserFilterModel(role=User.Role.user))

        if not users:
            await message.answer("Список пользователей пуст.")
            return

        msg = "Пользователи:\n"
        for user in users:
            username = f"@{user.username}" if user.username else "Без имени"
            msg += f"👤 {username} (ID: {user.telegram_id} Status:{user.verification_code.value})\n"
        answer = split_message(msg=msg, with_photo=False)
        for i in answer:
            await message.answer(i)
    except Exception as e:
        logger.error(f"Ошибка при получении списка юзеров - {e}")

@user_control_router.callback_query(VerifedCallback.filter())
async def admin_callback(
    query: CallbackQuery, callback_data: VerifedCallback
):
    user_id = callback_data.user_id
    logger.debug(f"Callback data: {callback_data}")
    try:
        async with async_session_maker() as session:
            if callback_data.action == "verified_user_yes":
                user:User = await UserDAO.find_one_or_none(session, TelegramIDModel(telegram_id=user_id))
                user.verification_status = User.VerifocationStatus.verifed
                await UserDAO.update(session=session,filters=TelegramIDModel(telegram_id=user_id),values=UserFilterModel.model_validate(user.to_dict()))
                await query.answer("Пользователь верифицирован")
                await query.message.delete()
                await query.bot.send_message(
                    user_id,
                    "Ваш аккаунт верифицирован, можете пользоваться ботом",
                    reply_markup=MainKeyboard.build_main_kb(user.role),
                )
                return
            if callback_data.action == "verified_user_no":

                user:User = await UserDAO.find_one_or_none(session, TelegramIDModel(telegram_id=user_id))
                user.verification_status = User.VerifocationStatus.verifed
                await UserDAO.update(session=session,filters=TelegramIDModel(telegram_id=user_id),values=UserFilterModel.model_validate(user.to_dict()))
                await query.answer("Пользователь заблокирован")
                await query.message.delete()
                await query.bot.send_message(
                    user_id,
                    "Сожалею, но ваш аккаунт был забанен. Дальнейшее пользование ботом не возможно",
                )
                return
    except Exception as e:
        logger.error(f"Ошибка при выполнении callback {callback_data.action}: {e}")
        await query.answer(
            "Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте снова позже."
        )
