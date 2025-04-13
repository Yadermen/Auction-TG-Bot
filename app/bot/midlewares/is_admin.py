from typing import Callable, Awaitable, Dict, Any, List

from aiogram import BaseMiddleware
from aiogram.types import Message
from app.db.dao import UserDAO
from app.db.database import async_session_maker


class CheckIsAdmin(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        async with async_session_maker() as session:
            admins = await UserDAO.find_all_admins(session)
            admin_ids: List[int] = [admin.telegram_id for admin in admins]

            if event.from_user.id in admin_ids:
                return await handler(event, data) 
            else:
                await event.answer(
                    "Только администраторы могут пользоваться этим функционалом"
                )
