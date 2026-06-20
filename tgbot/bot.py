import os
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from sc_client.client import connect, disconnect

import dotenv

from sc_handler import MACHINE_URL, send_message_to_sc, subscribe_to_message

dotenv.load_dotenv()

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")


async def start_command_handler(message: Message) -> None:
    await message.answer(
        "Привет! Я бот OSTIS Assistant.\n"
        "Используй /askai <вопрос>, чтобы отправить запрос облачному AI.\n"
        "Или просто напиши сообщение — я его получу и отвечу базово."
    )


async def ask_ai_command_handler(message: Message) -> None:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "Пожалуйста, отправьте команду в формате:\n"
            "/askai <ваш вопрос или запрос>."
        )
        return

    user_query = parts[1].strip()
    await message.answer(f"Вы спросили: {user_query}. В разработке.")


async def default_message_handler(message: Message) -> None:
    send_message_to_sc(message.text, str(message.from_user.id), message.from_user.first_name)
    await message.answer("✅ Сообщение отправлено. Ожидай ответ...")


async def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError(
            "Telegram bot token not found. Set TG_BOT_TOKEN or TELEGRAM_BOT_TOKEN environment variable."
        )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    loop = asyncio.get_event_loop()

    # Колбэк для SC-подписки — перекидывает ответ из SC (sync) в async event loop
    def handle_reply(tg_id: int, text: str) -> None:
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=tg_id, text=text),
            loop
        )

    subscribe_to_message(handle_reply)

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
