from aiogram.fsm.context import FSMContext
def split_message(msg: str, *, with_photo: bool) -> list[str]:
    """Split the text into parts considering Telegram limits."""
    parts = []
    while msg:
        # Determine the maximum message length based on
        # with_photo and whether it's the first iteration
        # (photo is sent only with the first message).
        if parts:
            max_msg_length = 4096
        elif with_photo:
            max_msg_length = 1024
        else:
            max_msg_length = 4096

        if len(msg) <= max_msg_length:
            # The message length fits within the maximum allowed.
            parts.append(msg)
            break

        # Cut a part of the message with the maximum length from msg
        # and find a position for a break by a newline character.
        part = msg[:max_msg_length]
        first_ln = part.rfind("\n")

        if first_ln != -1:
            # Newline character found.
            # Split the message by it, excluding the character itself.
            new_part = part[:first_ln]
            parts.append(new_part)

            # Trim msg to the length of the new part
            # and remove the newline character.
            msg = msg[first_ln + 1 :]
            continue

        # No newline character found in the message part.
        # Try to find at least a space for a break.
        first_space = part.rfind(" ")

        if first_space != -1:
            # Space character found. 
            # Split the message by it, excluding the space itself.
            new_part = part[:first_space]
            parts.append(new_part)
            
            # Trimming msg to the length of the new part
            # and removing the space.
            msg = msg[first_space + 1 :]
            continue

        # No suitable place for a break found in the message part.
        # Add the current part and trim the message to its length.
        parts.append(part)
        msg = msg[max_msg_length:]

    return parts

import re
TELEGRAM_ID_PATTERN = r'^[1-9]\d{6,9}$'
def is_valid_telegram_id(telegram_id: str) -> bool:
    return bool(re.match(TELEGRAM_ID_PATTERN, str(telegram_id)))

async def generate_lot_confirmation_text(state: FSMContext) -> str:
    """
    Формирует текст с информацией о лоте для подтверждения.
    """
    data = await state.get_data()
    confirmation_text = (
        f"Пожалуйста, подтвердите создание лота:\n\n"
        f"📋 Информация о лоте: {data.get('lot_info', 'Не указано')}\n"
        f"💰 Цена: {data.get('price', 'Не указано')} руб.\n"
        f"📈 Шаг ставки: {data.get('rate_step', 'Не указано')} руб.\n"
        f"⏳ Время: {data.get('time_in_minutes', 'Не указано')} минут\n"
        f"📷 Дополнительные фото: {data.get('photos_link', 'Не указано')}\n"
        f"📄 Ссылка на Автотеку: {data.get('autoteka_link', 'Не указано')}\n"
        f"🔧 Ссылка на диагностику: {data.get('diagnostik_link', 'Не указано')}\n\n"
        f"✅ Если всё верно, нажмите 'Подтвердить'."
    )
    return confirmation_text

def minutes_to_hours_and_minutes(total_minutes: int) -> str:
    """
    Переводит минуты в формат "X часов Y минут".
    
    :param total_minutes: Общее количество минут.
    :return: Строка в формате "X часов Y минут".
    """
    hours = total_minutes // 60
    minutes = total_minutes % 60
    result = f"{hours} часов {minutes} минут" if hours > 0 else f"{minutes} минут"
    return result