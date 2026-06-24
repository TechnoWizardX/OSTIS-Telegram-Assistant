import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from sc_client.client import connect, disconnect

import dotenv

from sc_handler import MACHINE_URL, send_message_to_sc, subscribe_to_message
from llm_helper import LLMHelper

dotenv.load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

BOT_TOKEN = os.environ.get("TG_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")

# Ключ OpenRouter. Получить на https://openrouter.ai/keys
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("LLM_TOKEN")

# Пути к md-файлам со знаниями. Лежат рядом с bot.py по умолчанию,
# но путь к правилам SCs можно переопределить через .env (SCS_RULES_PATH),
# если файл лежит в другом месте.
CONCEPTS_PATH = os.environ.get("CONCEPTS_PATH", "concepts.md")
SCS_RULES_PATH = os.environ.get("SCS_RULES_PATH", "scs_rules.md")

llm: LLMHelper | None = None  # инициализируется в main()


async def start_command_handler(message: Message) -> None:
    await message.answer(
        "Привет! Я бот OSTIS Assistant.\n\n"
        "Отправь интересующий тебя вопрос, и тебе ответит NIKA\n"
        "Если нужно что то подробнее разобрать, задавай свой вопрос LLM:\n"
        "/askai <вопрос>\n\n"
        "Например: /askai сделай больше примеров по SCs-коду\n\n"
        "Другие команды:\n"
        "/clear — очистить историю диалога с LLM\n"
    )


async def clear_command_handler(message: Message) -> None:
    if llm:
        llm.clear_history(message.from_user.id)
    await message.answer("История диалога очищена ✓")


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
    await _answer_with_llm(message, user_query)


async def default_message_handler(message: Message) -> None:
    # Обычные сообщения (без команды) больше НЕ уходят в LLM автоматически —
    # это сделано намеренно, чтобы не тратить лимит бесплатных моделей
    # на каждое случайное сообщение от 50 пользователей одновременно.
    # Вопрос к LLM нужно явно задавать через /askai <вопрос>.
    try:
        send_message_to_sc(
            message.text, str(message.from_user.id), message.from_user.first_name
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Не удалось отправить сообщение в sc-machine: %s", exc)

    await message.answer(
        "Подождите, NIKA сейчас ответит..."
    )


async def _answer_with_llm(message: Message, question: str) -> None:
    if llm is None:
        await message.answer("⚠️ LLM-модуль не инициализирован.")
        return

    if not question.strip():
        await message.answer("Напиши, пожалуйста, текст вопроса.")
        return

    thinking_msg = await message.answer("💭 Думаю над ответом...")
    answer = await llm.ask(tg_id=message.from_user.id, question=question)

    try:
        await thinking_msg.delete()
    except Exception:  # noqa: BLE001
        pass

    await message.answer(answer)


async def main() -> None:
    global llm

    if not BOT_TOKEN:
        raise RuntimeError(
            "Telegram bot token not found. Set TG_BOT_TOKEN or TELEGRAM_BOT_TOKEN environment variable."
        )

    llm = LLMHelper(
        api_key=OPENROUTER_API_KEY,
        concepts_path=CONCEPTS_PATH,
        scs_rules_path=SCS_RULES_PATH,
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    loop = asyncio.get_event_loop()

    def handle_reply(tg_id: int, text: str) -> None:
        asyncio.run_coroutine_threadsafe(
            bot.send_message(chat_id=tg_id, text=text, parse_mode="HTML"),
            loop
        )

    # Ожидаем готовности Nika: проверяем, что ключевые keynodes
    # разрешились в валидные адреса ДО создания подписки.
    # Если subscribe_to_message() создаст подписку на невалидный
    # ScAddr nrel_reply_to_message — она никогда не сработает.
    from sc_kpm import ScKeynodes
    for attempt in range(15):
        try:
            nrel = ScKeynodes["nrel_reply_to_message"]
            if nrel.is_valid():
                logger.info("SC-machine ready (attempt %d)", attempt + 1)
                break
        except (KeyError, RuntimeError):
            pass
        await asyncio.sleep(1)
    else:
        logger.warning("SC-machine not ready after 15s — reply sub may fail")

    subscribe_to_message(handle_reply)

    dp.message.register(start_command_handler, Command(commands=["start"]))
    dp.message.register(clear_command_handler, Command(commands=["clear"]))
    dp.message.register(ask_ai_command_handler, Command(commands=["askai"]))
    dp.message.register(default_message_handler)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        if llm:
            await llm.close()
        disconnect()


if __name__ == "__main__":
    connect(MACHINE_URL)
    asyncio.run(main())