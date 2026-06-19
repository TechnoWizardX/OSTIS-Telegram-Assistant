import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from sc_client.client import connect, disconnect, is_connected

import dotenv

from sc_handler import MACHINE_URL, send_message_to_sc

dotenv.load_dotenv()

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
SYSTEM_PROMPT = (
    "You are a helpful AI assistant for an OSTIS Telegram bot. "
    "Answer user requests clearly and concisely. "
    "If the user sends /askai, treat the following text as the actual request."
)


def create_ai_request(user_text: str) -> dict:
    """Подготавливает структуру запроса для AI.

    Этот метод формирует словарь с системным промптом
    и пользовательским запросом. Позже туда можно будет
    подставить вызов модели или API.
    """
    return {
        "system_prompt": SYSTEM_PROMPT,
        "user_prompt": user_text,
    }


async def start_command_handler(message: Message) -> None:
    """Обрабатывает команду /start.

    Отправляет приветственное сообщение и краткую инструкцию
    о том, как работать с ботом.
    """
    await message.answer(
        "Привет! Я бот OSTIS Assistant.\n"
        "Используй /askai <вопрос>, чтобы отправить запрос облачному AI.\n"
        "Или просто напиши сообщение — я его получу и отвечу базово."
    )


async def ask_ai_command_handler(message: Message) -> None:
    """Обрабатывает команду /askai.

    Разбирает текст команды, извлекает вопрос пользователя,
    создаёт заглушку запроса к AI и отвечает подтверждением.
    """
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Пожалуйста, отправьте команду в формате:\n"
            "/askai <ваш вопрос или запрос>."
        )
        return

    user_query = parts[1].strip()
    request_payload = create_ai_request(user_query)

    await message.answer("Я получил запрос и передаю его в AI-процесс.")
    await message.answer(
        "```System prompt:\n" + request_payload["system_prompt"] + "\n\n"
        "User prompt:\n" + request_payload["user_prompt"] + "```",
        parse_mode="Markdown",
    )


async def default_message_handler(message: Message) -> None:
    """Обрабатывает любое сообщение, которое не является командой.

    Это простой перехватчик, который отвечает пользователю
    """
    send_message_to_sc(message.text, str(message.from_user.id), message.from_user.first_name)
    await message.answer(
        f"Сообщение принято. Сейчас это заглушка. TG_ID: {message.from_user.id}, User Name: {message.from_user.first_name}"
    )


async def main() -> None:
    """Запускает бота и регистрирует обработчики.

    Проверяет наличие токена, создаёт экземпляр Bot и Dispatcher,
    регистрирует команды и запускает опрос Telegram.
    """
    if not BOT_TOKEN:
        raise RuntimeError(
            "Telegram bot token not found. Set TG_BOT_TOKEN or TELEGRAM_BOT_TOKEN environment variable."
        )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.register(start_command_handler, Command(commands=["start"]))
    dp.message.register(ask_ai_command_handler, Command(commands=["askai"]))
    dp.message.register(default_message_handler)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        disconnect()


if __name__ == "__main__":
    connect(MACHINE_URL)

    asyncio.run(main())
