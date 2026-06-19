from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Optional

from aiogram.types import Message, User


@dataclass
class TGUserData:
    """Структура данных пользователя Telegram.

    Этот класс хранит основные поля из объекта User и chat_id,
    чтобы их было удобно передавать между функциями бота.
    """

    user_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    language_code: Optional[str]
    is_bot: bool
    chat_id: int

    @property
    def full_name(self) -> str:
        """Возвращает полное имя пользователя, если есть first_name/last_name."""
        return " ".join(filter(None, [self.first_name, self.last_name]))

    def to_dict(self) -> dict:
        """Конвертирует объект в обычный словарь."""
        return asdict(self)


def from_user(user: User, chat_id: Optional[int] = None) -> TGUserData:
    """Создаёт TGUserData из объекта aiogram.types.User.

    Если chat_id не передан явно, используется user.id.
    """
    return TGUserData(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_bot=user.is_bot,
        chat_id=chat_id or user.id,
    )


def from_message(message: Message) -> TGUserData:
    """Создаёт TGUserData из сообщения Telegram.

    Использует message.from_user и message.chat.id.
    """
    if message.from_user is None:
        raise ValueError("Message must contain from_user information")
    return from_user(message.from_user, message.chat.id)


def get_user_id(message: Message) -> int:
    """Возвращает идентификатор пользователя из сообщения."""
    return from_message(message).user_id


def get_chat_id(message: Message) -> int:
    """Возвращает идентификатор чата из сообщения."""
    return from_message(message).chat_id


def get_username(message: Message) -> Optional[str]:
    """Возвращает имя пользователя (username) из сообщения."""
    return from_message(message).username
