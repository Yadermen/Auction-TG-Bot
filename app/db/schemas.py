from typing import Optional

from pydantic import BaseModel

from app.db.models import User


class TelegramIDModel(BaseModel):
    telegram_id: int

    class Config:
        from_attributes = True


class UserModel(TelegramIDModel):
    username: Optional[str]
    first_name: Optional[str]
    phone_number: Optional[str]
    user_enter_fio:Optional[str]
    last_name:Optional[str]
    verification_status: User.VerifocationStatus
    role: User.Role


class UserFilterModel(BaseModel):
    username: Optional[str] = None
    first_name: Optional[str] = None
    phone_number: Optional[str] = None
    user_enter_fio:Optional[str] = None
    last_name:Optional[str] = None
    verification_status: User.VerifocationStatus = None
    role: User.Role = None

class LotCreateModel(BaseModel):
    lot_info: str
    price: float
    rate_step: float
    time_in_minutes: int
    main_photo: str
    photos_link: str
    autoteka_link: str
    diagnostik_link: str
    curren_rate: Optional[float] = None
    current_rate_user_id: Optional[int] = None

    class Config:
        from_attributes = True

class LotFilterModel(BaseModel):
    id: Optional[int] = None
    lot_info: Optional[str] = None
    price: Optional[float] = None
    rate_step: Optional[float] = None
    time_in_minutes: Optional[int] = None
    main_photo: Optional[str] = None
    photos_link: Optional[str] = None
    autoteka_link: Optional[str] = None
    diagnostik_link: Optional[str] = None
    curren_rate: Optional[float] = None
    current_rate_user_id: Optional[int] = None

    class Config:
        from_attributes = True