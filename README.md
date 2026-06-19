# OSTIS Telegram Assistant 

> Диалоговая интеллектуальная система на базе [OSTIS](https://github.com/ostis-ai), интегрированная с Telegram.

**Ника** — это ассистент, построенный на технологиях семантических сетей (SC-код), который понимает запросы пользователей на естественном языке, классифицирует сообщения, выполняет логический вывод по продукционным правилам и формирует осмысленные ответы.

---

## Архитектура проекта

Проект состоит из четырёх основных компонентов:

```
┌────────────────────────────────────────────────────────┐
│                    Telegram Bot                        │
│                  (tgbot/ — aiogram)                    │
│  Принимает сообщения, передаёт в SC-машину,           │
│  возвращает ответы пользователю                        │
└──────────────────────┬─────────────────────────────────┘
                       │ ws://localhost:8090
┌──────────────────────▼─────────────────────────────────┐
│               Problem Solver (Python)                  │
│            (problem-solver/py/ — sc-kpm)               │
│  Модули классификации сообщений и логического вывода   │
└──────────────────────┬─────────────────────────────────┘
                       │ ws://localhost:8090
┌──────────────────────▼─────────────────────────────────┐
│                  SC-machine (C++)                       │
│         (install/sc-machine — ядро OSTIS)              │
│  Хранит и обрабатывает семантическую сеть (kb.bin)     │
└──────────────────────┬─────────────────────────────────┘
                       │
┌──────────────────────▼─────────────────────────────────┐
│                 База знаний (SCs)                       │
│                 (knowledge-base/)                       │
│  Онтологии, понятия, продукционные правила, темы       │
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│               Web-интерфейс (React)                    │
│              (interface/ — Webpack + Express)           │
│  Чат-интерфейс, WebRTC-звонки, сокеты                 │
└────────────────────────────────────────────────────────┘
```

---

## Компоненты

### 1. База знаний (`knowledge-base/`)

Семантическая сеть, написанная на языке **SCs** (SC-code). Содержит:

| Раздел | Описание |
|--------|----------|
| `ostis_knowledge/` | Базовые понятия SC-кода и темы формализации |
| `system/` | Системные сообщения, настроения (`mood/`), дисциплины (`disciplines/`) |
| `system/messages/` | Классы сообщений: известные/неизвестные пользователи, системные |
| `users/` | Классы пользователей: известный, неизвестный, студент |

Ключевые сущности БЗ:
- **Понятия** (`concept_*`) — классы объектов предметной области
- **Отношения** (`nrel_*`, `rrel_*`) — связи между понятиями
- **Логические продукции** (`nrel_reply_production`) — правила «ЕСЛИ-ТО»
- **Темы сообщений** (`concept_message_topic`) — классификация намерений пользователя

Подробный синтаксис SCs и правила написания продукций описаны в [scsrules.md](scsrules.md).

### 2. SC-machine (ядро OSTIS)

Высокопроизводительная машина обработки семантических сетей (C++). Устанавливается из исходников в `install/sc-machine/`.

- Хранит базу знаний в бинарном формате `kb.bin`
- Предоставляет WebSocket API на порту `8090`
- Конфигурация: [nika.ini](nika.ini)

### 3. Problem Solver (`problem-solver/py/`)

Python-сервер на базе `py-sc-kpm`, который регистрирует модули-обработчики:

- **MessageClassifyModule** — классифицирует входящие сообщения пользователя по темам
- Подключается к SC-machine через WebSocket
- Запускается командой: `./scripts/start.sh py_server`

### 4. Telegram Bot (`tgbot/`)

Асинхронный бот на [aiogram](https://aiogram.dev/) 3.x.

**Возможности:**
- Команда `/start` — приветствие и инструкция
- Команда `/ask-ai <вопрос>` — отправка запроса AI-процессу
- Произвольные сообщения — перехват и базовая обработка
- Подключение к SC-machine через `py-sc-client`

**Файлы:**
| Файл | Назначение |
|------|------------|
| `bot.py` | Основной модуль: инициализация, обработчики команд |
| `sc_handler.py` | Подключение/отключение к SC-machine |
| `tg_usr_data.py` | Датакласс данных пользователя Telegram |

### 5. Web-интерфейс (`interface/`)

Веб-приложение на React + TypeScript + Webpack:

- **Чат** с системой в реальном времени
- **WebRTC** для аудио/видео звонков между пользователями
- **Socket.IO** сервер (Express) для сигнализации звонков и списка онлайн-пользователей
- Redux для управления состоянием
- Адаптивная вёрстка

---

## Стек технологий

| Слой | Технологии |
|------|------------|
| **Ядро** | SC-machine (C++), SCs-код |
| **Problem Solver** | Python 3, py-sc-kpm, py-sc-client |
| **Telegram Bot** | Python 3, aiogram 3.x, python-dotenv |
| **Frontend** | React, TypeScript, Redux, Webpack, Express, Socket.IO, WebRTC |
| **Форматирование** | Clang-format (C++), Prettier (JS/TS) |

---

## Установка и запуск

### Предварительные требования

- **ОС:** Ubuntu 20.04+ (рекомендуется)
- **Python:** 3.10+
- **Node.js:** 18+
- **Компилятор C++:** GCC 11+ или Clang 14+
- **Системные зависимости:** `build-essential`, `cmake`, `libboost-all-dev`

### 1. Сборка SC-machine

```bash
# Клонирование и сборка sc-machine (OSTIS)
# Следуйте инструкциям: https://github.com/ostis-ai/sc-machine
# Результат сборки ожидается в install/sc-machine/
```

### 2. Установка Python-зависимостей

```bash
# Общие зависимости
pip install -r requirements.txt

# Problem Solver
cd problem-solver/py
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Сборка базы знаний

```bash
./scripts/start.sh build_kb
```

### 4. Настройка переменных окружения

Создайте файл `.env`:

```env
# Telegram Bot Token (получить у @BotFather)
TG_BOT_TOKEN=your_telegram_bot_token

# Альтернативное имя переменной
# TELEGRAM_BOT_TOKEN=your_telegram_bot_token
```

### 5. Запуск всех компонентов

```bash
# Запуск всего в трёх терминалах (build → machine → web → interface)
./launch.sh

# Или по отдельности:
./scripts/start.sh build_kb   # Сборка БЗ
./scripts/start.sh machine    # SC-machine (порт 8090)
./scripts/start.sh web        # Web-сервер (sc-web)
./scripts/start.sh interface  # Frontend (Webpack dev-server)
./scripts/start.sh py_server  # Problem Solver (Python)
```

### 6. Запуск Telegram-бота

```bash
cd tgbot
python bot.py
```

### Управление

```bash
./launch.sh     # Запуск всех терминалов
./restart.sh    # Перезапуск всех терминалов
./rebuild.sh    # Пересборка БЗ + перезапуск только terminal1
```

---

## Структура файлов

```
├── knowledge-base/          # База знаний (SCs-код)
│   ├── ostis_knowledge/     # Базовые понятия SC-кода
│   ├── system/              # Системные сущности
│   │   ├── messages/        # Классы сообщений
│   │   ├── disciplines/     # Дисциплины
│   │   └── mood/            # Настроения
│   └── users/               # Классы пользователей
├── problem-solver/          # Решатель задач
│   └── py/                  # Python-модули (sc-kpm)
│       └── server.py        # Точка входа
├── tgbot/                   # Telegram-бот
│   ├── bot.py               # Основной модуль
│   ├── sc_handler.py        # Подключение к SC-machine
│   └── tg_usr_data.py       # Данные пользователя
├── interface/               # Web-интерфейс
│   ├── src/                 # React-приложение
│   ├── server/server.js     # Socket.IO + Express сервер
│   └── webpack/             # Конфигурация Webpack
├── scripts/                 # Скрипты
│   ├── start.sh             # Запуск компонентов
│   └── clang/               # Форматирование C++
├── install/                 # Собранные компоненты (sc-machine, nika)
├── launch.sh                # Запуск всех терминалов
├── restart.sh               # Перезапуск
├── rebuild.sh               # Пересборка БЗ
├── nika.ini                 # Конфигурация SC-machine
├── repo.path                # Пути компонентов БЗ
├── repo-patch.path          # Патч-пути БЗ
├── scsrules.md              # Правила написания SCs-кода
└── requirements.txt         # Python-зависимости
```

---

## Лицензия

Проект распространяется под лицензией MIT. См. [LICENSE](LICENSE).

---

## Ссылки

- [OSTIS Technology](https://github.com/ostis-ai)
- [SC-machine](https://github.com/ostis-ai/sc-machine)
- [py-sc-client](https://github.com/ostis-ai/py-sc-client)
- [py-sc-kpm](https://github.com/ostis-ai/py-sc-kpm)
- [aiogram](https://aiogram.dev/)
