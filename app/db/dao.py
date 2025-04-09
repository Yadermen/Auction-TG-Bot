from loguru import logger
from sqlalchemy import or_, select
from sqlalchemy.exc import SQLAlchemyError
from app.db.base import BaseDAO
from app.db.models import User,Lot
from sqlalchemy.ext.asyncio import AsyncSession


class UserDAO(BaseDAO[User]):
    model = User
    
    @classmethod
    async def find_all_admins(cls, session: AsyncSession):
        """Найти всех пользователей с ролью admin"""
        logger.info("Поиск всех администраторов")
        try:
            query = select(cls.model).where(cls.model.role == cls.model.Role.admin)
            result = await session.execute(query)
            admins = result.scalars().all()
            logger.info(f"Найдено {len(admins)} администраторов")
            return admins
        except SQLAlchemyError as e:
            logger.error(f"Ошибка при поиске администраторов: {e}")
            raise

class LotDAO(BaseDAO[Lot]):
    model = Lot
