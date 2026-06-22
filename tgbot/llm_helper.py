"""
llm_helper.py

Модуль для общения с LLM через OpenRouter.

Что делает:
  1. Загружает concepts.md (понятия предметной области) и scs_rules.md
     (правила написания SCs-кода) с диска один раз при старте.
  2. Хранит системный промпт с этими знаниями.
  3. Хранит отдельную историю диалога для каждого пользователя Telegram
     (по tg_id), чтобы разные пользователи не путали друг друга контекст.
  4. Отправляет запрос к OpenRouter с фолбэком на другую бесплатную модель,
     если основная модель недоступна / превышен rate limit.

Использование (в bot.py):

    from llm_helper import LLMHelper

    llm = LLMHelper(
        api_key=os.environ["OPENROUTER_API_KEY"],
        concepts_path="concepts.md",
        scs_rules_path="scs_rules.md",   # путь можно поменять
    )

    answer = await llm.ask(tg_id=message.from_user.id, question=user_text)
"""

import os
import logging
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger("llm_helper")


# ---------------------------------------------------------------------------
# Модели OpenRouter (все проверены на бесплатность — пометка :free,
# $0 input / $0 output на момент проверки, июнь 2026)
# ---------------------------------------------------------------------------
# Основная модель — Qwen3 Coder: 1M токенов контекста, специализирована на
# коде (хорошо подходит для объяснения и проверки SCs-кода), бесплатна.
#
# Фолбэк-модели применяются по очереди, если предыдущая вернула ошибку
# (429 — rate limit, 404 — модель временно недоступна / снята с :free,
# 5xx — провайдер недоступен, и т.п.). Список отсортирован по убыванию
# контекстного окна и пригодности для кода/рассуждений.
PRIMARY_MODEL = "qwen/qwen3-coder:free"

FALLBACK_MODELS = [
    "deepseek/deepseek-chat-v3.1:free",     # 1M контекст, сильная резервная модель
    "meta-llama/llama-4-maverick:free",     # 1M контекст, мультимодальная
    "meta-llama/llama-4-scout:free",        # ~10M контекст, быстрее Maverick
    "z-ai/glm-4.5-air:free",                # большой контекст, сильна в код/рассуждениях
    "deepseek/deepseek-r1:free",            # сильное рассуждение, не лучший контекст
    "poolside/laguna-m.1:free",             # 256K контекст, агентный коддинг
    "mistralai/mistral-7b-instruct:free",   # лёгкий, надёжный последний рубеж
]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Сколько последних сообщений (пар вопрос-ответ) хранить на пользователя.
# При 50 одновременных пользователях это держит память бота в разумных
# пределах и не раздувает каждый запрос к LLM.
MAX_HISTORY_MESSAGES = 20  # 10 пар вопрос/ответ


def _read_md_file(path: Optional[str]) -> str:
    """Безопасно читает md-файл. Если файла нет — возвращает пояснение,
    чтобы бот не падал, а просто работал без этого знания."""
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        logger.warning("Файл знаний не найден: %s", p.resolve())
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.error("Не удалось прочитать файл %s: %s", p, exc)
        return ""


class LLMHelper:
    def __init__(
        self,
        api_key: str,
        concepts_path: str = "concepts.md",
        scs_rules_path: Optional[str] = None,
        primary_model: str = PRIMARY_MODEL,
        fallback_models: Optional[list] = None,
        site_url: str = "https://github.com/",
        app_name: str = "OSTIS Telegram Assistant",
    ):
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY не задан. Добавь его в .env "
                "(OPENROUTER_API_KEY=sk-or-v1-...)."
            )

        self.api_key = api_key
        self.primary_model = primary_model
        self.fallback_models = fallback_models or FALLBACK_MODELS
        self.site_url = site_url
        self.app_name = app_name

        self.concepts_path = concepts_path
        self.scs_rules_path = scs_rules_path

        # Загружаем оба файла один раз при старте бота.
        self._concepts_text = _read_md_file(concepts_path)
        self._scs_rules_text = _read_md_file(scs_rules_path)

        if not self._concepts_text:
            logger.warning(
                "concepts.md пуст или не найден (%s) — бот будет отвечать "
                "без знаний о понятиях.", concepts_path
            )
        if scs_rules_path and not self._scs_rules_text:
            logger.warning(
                "Файл правил SCs пуст или не найден (%s).", scs_rules_path
            )

        self._system_prompt = self._build_system_prompt()

        # История диалогов по каждому пользователю отдельно.
        # tg_id -> list[{"role": "user"/"assistant", "content": str}]
        self._histories: dict[int, list[dict]] = {}

        self._client = httpx.AsyncClient(timeout=60.0)

    # ------------------------------------------------------------------
    # Построение системного промпта
    # ------------------------------------------------------------------
    def _build_system_prompt(self) -> str:
        parts = [
            "Ты — ассистент по изучению технологии OSTIS и SC-кода.",
            "Отвечай простым и понятным языком, как для новичка, "
            "избегай излишне академичных формулировок.",
            "Если вопрос касается понятия из базы знаний ниже — "
            "объясняй именно на основе этого описания, не выдумывай.",
            "Если информации по вопросу нет ни в понятиях, ни в правилах "
            "SCs — честно скажи, что не знаешь, и предложи переформулировать.",
            "Отвечай на языке, на котором пишет пользователь "
            "(по умолчанию — русский).",
        ]

        if self._concepts_text:
            parts.append(
                "\n\n=== ПОНЯТИЯ ПРЕДМЕТНОЙ ОБЛАСТИ (concepts.md) ===\n"
                + self._concepts_text
            )

        if self._scs_rules_text:
            parts.append(
                "\n\n=== ПРАВИЛА НАПИСАНИЯ SCs-КОДА ===\n"
                + self._scs_rules_text
                + "\n\nКогда пользователь просит написать или проверить "
                "SCs-код, строго следуй этим правилам."
            )

        return "\n".join(parts)

    def reload_knowledge(self) -> None:
        """Перечитать concepts.md и scs_rules.md без перезапуска бота
        (например, если файлы обновили на диске)."""
        self._concepts_text = _read_md_file(self.concepts_path)
        self._scs_rules_text = _read_md_file(self.scs_rules_path)
        self._system_prompt = self._build_system_prompt()
        logger.info("Файлы знаний перезагружены.")

    # ------------------------------------------------------------------
    # История диалогов по пользователям
    # ------------------------------------------------------------------
    def _get_history(self, tg_id: int) -> list[dict]:
        return self._histories.setdefault(tg_id, [])

    def _append_history(self, tg_id: int, role: str, content: str) -> None:
        history = self._get_history(tg_id)
        history.append({"role": role, "content": content})
        # Обрезаем старые сообщения, чтобы не раздувать запрос
        if len(history) > MAX_HISTORY_MESSAGES:
            del history[: len(history) - MAX_HISTORY_MESSAGES]

    def clear_history(self, tg_id: int) -> None:
        """Очистить историю конкретного пользователя (команда /clear)."""
        self._histories[tg_id] = []

    # ------------------------------------------------------------------
    # Запрос к OpenRouter с фолбэком моделей
    # ------------------------------------------------------------------
    async def _call_openrouter(self, model: str, messages: list[dict]) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            # Эти два заголовка рекомендует OpenRouter для рейтингов /
            # приоритезации бесплатных моделей. Не обязательны, но полезны.
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.4,
            "max_tokens": 1200,
        }

        response = await self._client.post(
            OPENROUTER_URL, headers=headers, json=payload
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenRouter вернул {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise RuntimeError(f"Неожиданный формат ответа OpenRouter: {data}") from exc

    async def _call_with_fallback(self, messages: list[dict]) -> str:
        models_to_try = [self.primary_model, *self.fallback_models]
        last_error: Optional[Exception] = None

        for model in models_to_try:
            try:
                logger.info("Запрос к модели %s", model)
                return await self._call_openrouter(model, messages)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Модель %s недоступна: %s", model, exc)
                last_error = exc
                continue

        raise RuntimeError(
            f"Все модели недоступны. Последняя ошибка: {last_error}"
        )

    # ------------------------------------------------------------------
    # Публичный метод — то, что вызывает бот
    # ------------------------------------------------------------------
    async def ask(self, tg_id: int, question: str) -> str:
        """Задать вопрос LLM с учётом истории конкретного пользователя
        и загруженных знаний (concepts.md + scs_rules.md)."""

        self._append_history(tg_id, "user", question)

        messages = [
            {"role": "system", "content": self._system_prompt},
            *self._get_history(tg_id),
        ]

        try:
            answer = await self._call_with_fallback(messages)
        except Exception as exc:  # noqa: BLE001
            logger.error("Не удалось получить ответ от LLM: %s", exc)
            return (
                "⚠️ Не получилось получить ответ от модели "
                "(возможно, превышен лимит запросов). Попробуй ещё раз "
                "через минуту."
            )

        self._append_history(tg_id, "assistant", answer)
        return answer

    async def close(self) -> None:
        await self._client.aclose()