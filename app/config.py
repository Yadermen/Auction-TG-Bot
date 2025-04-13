
import os
from typing import List
from urllib.parse import quote
from loguru import logger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: List[int]

    USER_GROUP_ID:int
    ADMIN_GROUP_ID:int

    FORMAT_LOG: str = "{time:YYYY-MM-DD at HH:mm:ss} | {level} | {message}"
    LOG_ROTATION: str = "10 MB"
    DB_URL: str = 'sqlite+aiosqlite:///data/db.sqlite3'

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
    )


# Инициализация конфигурации
settings = Settings()

def setup_logger(app_name: str):
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log")
    os.makedirs(log_dir, exist_ok=True)
    logger.add(
        os.path.join(log_dir, f"log_{app_name}.txt"),
        format=settings.FORMAT_LOG,
        level="INFO",
        rotation=settings.LOG_ROTATION
    )
    logger.add(
        os.path.join(log_dir, f"log_{app_name}_error.txt"),
        format=settings.FORMAT_LOG,
        level="ERROR",
        rotation=settings.LOG_ROTATION
    )

bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())
admins = settings.ADMIN_IDS