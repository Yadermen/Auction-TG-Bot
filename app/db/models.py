import enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    BigInteger,
    Boolean,
    Enum,
    ForeignKey,
    Integer,
    String,
    Float
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

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, primary_key=True)
    username: Mapped[Optional[str]] = mapped_column(String, default=None)
    first_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    last_name: Mapped[Optional[str]] = mapped_column(String, default=None)
    user_enter_fio: Mapped[Optional[str]] = mapped_column(String, default=None)
    phone_number: Mapped[Optional[str]] = mapped_column(String, default=None)
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.user)
    verification_status: Mapped[VerifocationStatus] = mapped_column(Enum(VerifocationStatus),
                                                                    default=VerifocationStatus.non_verifed)

    lots_rate = relationship("Lot", back_populates="user_rate")


class Lot(Base):
    __tablename__ = "lots"
    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)

    lot_info: Mapped[str] = mapped_column(String)
    price: Mapped[float] = mapped_column(Float)
    rate_step: Mapped[float] = mapped_column(Float)
    time_in_minutes: Mapped[int] = mapped_column(Integer)
    main_photo: Mapped[str] = mapped_column(String)
    photos_link: Mapped[str] = mapped_column(String)
    autoteka_link: Mapped[str] = mapped_column(String)
    diagnostik_link: Mapped[str] = mapped_column(String)
    curren_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    current_rate_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.telegram_id"),
                                                                nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)

    user_rate = relationship("User", back_populates="lots_rate")
