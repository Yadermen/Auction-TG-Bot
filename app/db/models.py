from datetime import datetime
import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    JSON,
    BigInteger,
    Column,
    DateTime,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from typing import Optional
from app.db.database import Base


class User(Base):
    class Role(enum.Enum):
        admin = "admin"
        user = "user"

    class VerifocationStatus(enum.Enum):
        verifed = "verifed"
        non_verifed = "non_verifed"
        banned = "banned"

    __tablename__ = "users"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String, default=None)
    first_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    last_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    user_enter_fio: Mapped[Optional[str]] = mapped_column(String, default=None)
    phone_number: Mapped[Optional[str]] = mapped_column(String, default=None)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.user)
    verification_status: Mapped[VerifocationStatus] = mapped_column(Enum(VerifocationStatus),default=VerifocationStatus.non_verifed)

class Lot(Base):
    __tablename__ = "lots"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    lot_info: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(BigInteger)
    rate_step: Mapped[float] = mapped_column(BigInteger)
    time_in_minutes: Mapped[int] = mapped_column(BigInteger)
    main_photo: Mapped[str] = mapped_column(String)
    photos_link: Mapped[str] = mapped_column(String)
    autoteka_link: Mapped[str] = mapped_column(String)
    diagnostik_link: Mapped[str] = mapped_column(String)
    curren_rate:Mapped[float] = mapped_column(BigInteger)