# Nika — справочная система по инструментальным средствам OSTIS
## Выжимка формализованных объектов базы знаний и кода tgbot

---

## 1. База знаний (SCs-код)

### 1.1. Дисциплины (concept_discipline)

| Системный idtf | nrel_main_idtf |
|---|---|
| `ostis_basics_discipline` | Основы OSTIS |
| `topic_basics_of_formalization` | Основы формализации на SC-коде |
| `topic_python_libraries` | Python библиотеки |

### 1.2. Темы дисциплин (concept_discipline_topic)

| Системный idtf | nrel_main_idtf | Ключевые понятия |
|---|---|---|
| `sc_code_topic` | Основные понятия SC-кода | concept_sc_code, sc_element, sc_construction, sc_set, sc_structure, sc_text, sc_knowledge, sc_file, sc_idtf, main_sc_idtf |
| `sc_syntax_topic` / `concept_sc_syntax` | Синтаксис SC-кода | concept_sc_alphabet, concept_sc_element_classification, concept_sc_node, concept_sc_connector, concept_sc_edge, concept_sc_arc, nrel_incidence, nrel_incidence_second |
| `topic_py_sc_client` | Библиотека py-sc-client | concept_work_with_sc_server, concept_scaddr, concept_sctype, concept_scconstruction, concept_sctemplate, concept_sc_type_usage_in_templates, concept_sc_link_content, concept_sc_event_subscription |
| `topic_py_sc_kpm` | Библиотека py-sc-kpm | concept_sckeynodes, concept_sc_agent_classic, concept_sc_server_module, concept_sc_kpm_utils, concept_action_utils |

### 1.3. Синтаксические классы SC-кода (concept_sc_syntax)

**Алфавит Ядра** (`concept_sc_alphabet`): 5 базовых классов:
- `concept_sc_node_nonfile` — узел, не знак файла
- `concept_sc_node_file_sign` — узел-знак файла
- `concept_sc_edge` — неориентированный коннектор (ребро)
- `concept_sc_arc_general` — дуга общего вида
- `concept_sc_arc_main` — дуга принадлежности

**Иерархия узлов:** `concept_sc_node` → `concept_sc_node_nonfile` / `concept_sc_node_file_sign`; по постоянству: `constant` / `variable`.

**Иерархия коннекторов:** `concept_sc_connector` → `concept_sc_edge` (constant/variable) + `concept_sc_arc` → `concept_sc_arc_general` / `concept_sc_arc_main` → `permanent` / `temporal` (actual/nonactual) / `positive` / `negative` / `fuzzy`.

**Отношения инцидентности:** `nrel_incidence`, `nrel_incidence_second`.

### 1.4. SC-идентификаторы и внешние представления

**Идентификаторы** (`concept_sc_idtf`): `simple_sc_idtf`, `complex_sc_idtf`, `sc_expression`, `main_sc_idtf`, `sc_idtf_family`, `string_sc_idtf`, `nonstring_sc_idtf`, `sc_idtf_system`, `system_sc_id`, `basic_rules_for_constructing_simple_sc_string_identifiers_of_certain_entity_classes_on_the_SCcode`.

**Внешние представления** (`concept_sc_external_representation`): `concept_scg_code` (графический), `concept_scs_code` (строковый), `concept_scn_code` (гипертекстовый).

### 1.5. Дисциплина «Основы OSTIS» — ключевые понятия

- `concept_ostis` — технология OSTIS (определение + пояснение).
- `concept_ostis_project` — проект OSTIS: определение, пояснение, обоснование (`nrel_rationale`), принципы (`nrel_principles`), преимущества (`nrel_advantages`), ключевые выводы (`nrel_key_takeaways`), примечание (`nrel_note`).

### 1.6. Дисциплина «Python библиотеки» — ключевые понятия

#### py-sc-client (`topic_py_sc_client`)

| Понятие | Суть |
|---|---|
| `concept_work_with_sc_server` | Подключение: `connect(url)`, `is_connected()`, `disconnect()` |
| `concept_scaddr` | Адрес sc-элемента: поле `value`, метод `is_valid()` |
| `concept_sctype` | Тип элемента: битовые флаги CONST_/VAR_, NODE/NODE_LINK/COMMON_ARC/PERM_POS_ARC/... |
| `concept_scconstruction` | Пакетное создание: `generate_node`, `generate_link`, `generate_connector` + `generate_elements()` |
| `concept_sctemplate` | Шаблон: `triple(источник, дуга, цель)` / `quintuple(источник, COMMON, цель, PERM_POS, отношение)` + `search_by_template()` / `generate_by_template()` |
| `concept_sc_type_usage_in_templates` | Золотое правило квинтупла: позиция 2 = VAR_COMMON_ARC, позиция 4 = VAR_PERM_POS_ARC |
| `concept_sc_link_content` | Ссылки: `get_link_content(addr)`, `search_links_by_contents(contents)`, типы STRING/INT/FLOAT |
| `concept_sc_event_subscription` | Подписка: `ScEventSubscriptionParams(addr, ScEventType, callback)` + `create_elementary_event_subscriptions()` |

#### py-sc-kpm (`topic_py_sc_kpm`)

| Понятие | Суть |
|---|---|
| `concept_sckeynodes` | Кеш кейноудов: `ScKeynodes["idtf"]`, `ScKeynodes.get("idtf")`, `ScKeynodes.resolve("idtf", type)`, `rrel_index(n)` |
| `concept_sc_agent_classic` | Агент: `super().__init__("action_class")`, `on_event(src, connector, action_addr) -> ScResult.OK/SKIP` |
| `concept_sc_server_module` | `ScServer("ws://...")`, `server.add_modules()`, `server.serve()` + контекстные менеджеры |
| `concept_sc_kpm_utils` | Утилиты: `generate_node/link/connector`, `generate_non_role_relation`, `search_element_by_non_role_relation`, `get_link_content_data` |
| `concept_action_utils` | Действия: `generate_action`, `generate_role_relation`, `get_action_arguments`, `finish_action_with_status` |

### 1.7. Учебный план (study_plan.scs)

7 дней (`study_day_1`...`study_day_7`):
1. Философия и архитектура OSTIS
2. Анатомия SC-кода — базовые элементы
3. От конструкций к знаниям
4. Синтаксис Ядра — Алфавит и SC-узлы
5. Синтаксис Ядра — SC-коннекторы
6. Внешний мир — Идентификаторы и языки
7. Практикум формализации и экосистема

Каждый день: `nrel_key_concepts` (множество понятий), `nrel_definition`, `nrel_explanation`.

---

## 2. Код Telegram-бота (tgbot/)

### 2.1. `bot.py` — основной модуль

**Константы и глобальные переменные:**
- `BOT_TOKEN` ← `TG_BOT_TOKEN` или `TELEGRAM_BOT_TOKEN` (из .env)
- `OPENROUTER_API_KEY` ← `OPENROUTER_API_KEY` или `LLM_TOKEN` (из .env)
- `CONCEPTS_PATH` ← `"concepts.md"` (переопределяется через `CONCEPTS_PATH`)
- `SCS_RULES_PATH` ← `"scs_rules.md"` (переопределяется через `SCS_RULES_PATH`)
- `llm: LLMHelper | None` — глобальный экземпляр LLM-помощника

**Обработчики команд (aiogram 3.x):**

| Функция | Триггер | Действие |
|---|---|---|
| `start_command_handler(message)` | `/start` | Приветствие + инструкция по /askai |
| `clear_command_handler(message)` | `/clear` | `llm.clear_history(tg_id)` → «История очищена» |
| `ask_ai_command_handler(message)` | `/askai <вопрос>` | Извлекает вопрос после команды → `_answer_with_llm(message, question)` |
| `default_message_handler(message)` | любое обычное сообщение | `send_message_to_sc(text, tg_id, user_name)` → подсказка использовать /askai |

**Вспомогательные:**
- `_answer_with_llm(message, question)` — отправляет «💭 Думаю...», вызывает `llm.ask(tg_id, question)`, удаляет статус, отправляет ответ.

**`main()` — точка входа:**
1. Проверяет `BOT_TOKEN`
2. Создаёт `LLMHelper(api_key, concepts_path, scs_rules_path)`
3. Создаёт `Bot(token)` и `Dispatcher()`
4. Определяет `handle_reply(tg_id, text)` — отправка ответа в Telegram через `bot.send_message()` с `parse_mode="HTML"`
5. Ждёт готовности SC-machine (до 15 попыток по 1 сек): проверяет `ScKeynodes["nrel_reply_to_message"].is_valid()`
6. Вызывает `subscribe_to_message(handle_reply)`
7. Регистрирует 4 хендлера
8. Запускает `dp.start_polling(bot)`, в finally — закрывает сессию, `llm.close()`, `disconnect()`

**Запуск:** `connect(MACHINE_URL)`, затем `asyncio.run(main())`.

### 2.2. `sc_handler.py` — взаимодействие с SC-машиной

**Константа:** `MACHINE_URL = "ws://localhost:8090"`

**Функции:**

| Функция | Сигнатура | Назначение |
|---|---|---|
| `get_user_class` | `(tg_id: str, user_name: str) -> str` | Ищет пользователя по tg_id → проверяет `_is_student()` → возвращает `"concept_student"`, `"concept_user"` или `"concept_unknown_user"` |
| `_search_user_by_tg_id` | `(tg_id: str) -> ScAddr` | `search_links_by_contents(tg_id)` → перебирает все ссылки → для каждой строит quintuple-шаблон с `nrel_user_id` → возвращает ScAddr пользователя или пустой |
| `_resolve_myself` | `() -> ScAddr` | Ищет узел `myself`: triple `concept_intelligent_system → VAR_PERM_POS_ARC → VAR_NODE` |
| `_is_student` | `(user_addr: ScAddr) -> bool` | Проверяет triple `concept_student → VAR_PERM_POS_ARC → user_addr` |
| `send_message_to_sc` | `(message: str, tg_id: str, user_name: str) -> None` | Определяет класс пользователя → если unknown: `sign_up_new_user()` → создаёт ScLink с текстом → `generate_by_template()` для `nrel_message_author` |
| `sign_up_new_user` | `(tg_id: str, user_name: str) -> ScAddr` | Создаёт ссылки tg_id и имени + узел пользователя → устанавливает `nrel_user_id`, `<- concept_student`, `nrel_main_idtf` → сохраняет .scs-файл в `knowledge-base/users/tgusers/` → устанавливает `nrel_known_user` между myself и пользователем |
| `subscribe_to_message` | `(message_adder: Callable | None) -> list` | Подписывается на `AFTER_GENERATE_OUTGOING_ARC` от `nrel_reply_to_message`. Колбэк: находит reply-сообщение → исходное сообщение → автора → tg_id автора → вызывает `message_adder(tg_id, text)` |

### 2.3. `llm_helper.py` — LLM-интеграция (OpenRouter)

**Константы:**
- `PRIMARY_MODEL = "qwen/qwen3-coder:free"`
- `FALLBACK_MODELS` — список из 7 моделей (deepseek-chat-v3.1, llama-4-maverick, llama-4-scout, glm-4.5-air, deepseek-r1, laguna-m.1, mistral-7b)
- `MAX_HISTORY_MESSAGES = 20`

**Класс `LLMHelper`:**

| Метод | Сигнатура | Назначение |
|---|---|---|
| `__init__` | `(api_key, concepts_path, scs_rules_path, primary_model, fallback_models, site_url, app_name)` | Загружает concepts.md и scs_rules.md с диска → формирует `_system_prompt` → создаёт `httpx.AsyncClient` |
| `_build_system_prompt` | `() -> str` | Собирает системный промпт: роль ассистента OSTIS + полный текст concepts.md + полный текст scs_rules.md |
| `reload_knowledge` | `() -> None` | Перечитывает md-файлы с диска без перезапуска |
| `_get_history` | `(tg_id: int) -> list[dict]` | Возвращает историю диалога пользователя (словарь `{tg_id: [messages]}`) |
| `_append_history` | `(tg_id, role, content)` | Добавляет сообщение + обрезает до MAX_HISTORY_MESSAGES |
| `clear_history` | `(tg_id: int) -> None` | Очищает историю пользователя |
| `_call_openrouter` | `(model, messages) -> str` | POST на `https://openrouter.ai/api/v1/chat/completions`, возвращает `choices[0].message.content` |
| `_call_with_fallback` | `(messages) -> str` | Пробует PRIMARY_MODEL → FALLBACK_MODELS по очереди при ошибках |
| `ask` | `(tg_id: int, question: str) -> str` | Добавляет вопрос в историю → вызывает `_call_with_fallback` → добавляет ответ в историю → возвращает ответ |
| `close` | `() -> None` | Закрывает httpx-клиент |

### 2.4. `logger.py` — логирование

**Функция:** `log(message, level="info", system="unknown")` — печатает `[timestamp][system][LEVEL] message`.

---

## 3. Вспомогательные md-файлы (tgbot/)

- **`concepts.md`** — описания всех понятий предметной области (OSTIS, SC-код, синтаксис, py-sc-client, py-sc-kpm, системные сущности, продукции). Загружается в системный промпт LLM.
- **`scs_rules.md`** — правила написания SCs-кода: синтаксис коннекторов, структура понятия, структура темы сообщения, логические продукции, подстановки в шаблонах, частые отношения (nrel_*, rrel_*), типовые ошибки, соглашения об именовании.
