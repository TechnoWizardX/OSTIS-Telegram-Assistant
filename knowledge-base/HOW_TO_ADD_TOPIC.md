## Подробная шпаргалка: Как добавлять темы и понятия в БЗ Ники

---

### 🏗 Архитектура БЗ (как устроена иерархия)

```
Дисциплина (concept_discipline)
  └── Тема (concept_discipline_topic)
        └── Понятие (concept) — отдельный .scs файл
```

Пример для ИИ:
```
topic_ai (concept_discipline)
  ├── topic_1_ai_concepts (concept_discipline_topic)
  │     ├── concept_problem_solver (concept)
  │     ├── concept_knowledge_base (concept)
  │     └── ...
  └── topic_2_ai_directions (concept_discipline_topic)
        ├── symbolic_ai
        ├── connectionist_ai
        └── hybrid_ai
```

---

### 📋 Чек-лист: Добавление НОВОЙ ТЕМЫ

#### Шаг 1: Создать файл темы

Создать файл `knowledge-base/.../topic_<name>.scs`:

```
topic_my_topic
<- concept_discipline_topic;          ← ⚠️ ОБЯЗАТЕЛЬНО concept_discipline_topic (НЕ sc_node_class!)
=> nrel_main_idtf:
    [Название темы]
    (*
        <- lang_ru;;
    *);;
=> nrel_explanation:
    [Краткое описание темы — что в ней изучается.]
    (*
        <- concept_explanation;;
    *);;
=> nrel_key_concepts: {
    concept_xxx;
    concept_yyy;
    concept_zzz
};;
```

**Ключевые поля:**
| Поле | Обязательность | Описание |
|------|---------------|----------|
| `<- concept_discipline_topic` | ✅ ОБЯЗАТЕЛЬНО | Тип узла — БЕЗ этого тема не находится продакшенами |
| `nrel_main_idtf` | ✅ ОБЯЗАТЕЛЬНО | Название темы (то, что видит пользователь) |
| `nrel_explanation` | ✅ ОБЯЗАТЕЛЬНО | Описание темы (для ответа бота) |
| `nrel_key_concepts` | ✅ ОБЯЗАТЕЛЬНО | Список понятий темы через `;` |
| `nrel_definition` | ⚡ Желательно | Определение темы |
| `nrel_purpose` | ⚡ Желательно | Цели изучения темы |
| `nrel_key_questions` | ⚡ Желательно | Ключевые вопросы темы |
| `nrel_materials` | ⚡ Желательно | Полезные ссылки |
| `nrel_idtf` | 🔧 Опционально | Альтернативное название (например, «Тема 1») |

---

#### Шаг 2: Создать файлы понятий

Для каждого понятия из `nrel_key_concepts` создать отдельный `.scs` файл:

```
concept_xxx
<= nrel_inclusion: topic_my_topic;    ← Связь с темой
<- concept;                           ← Тип — concept
=> nrel_main_idtf:
    [название понятия на русском]
    (*
        <- lang_ru;;
    *);;
=> nrel_definition:
    [Что такое XXX — определение.]
    (*
        <- concept_definition;;
        <- lang_ru;;
    *);;
=> nrel_explanation:
    [Подробное пояснение — зачем нужно, как используется.]
    (*
        <- concept_explanation;;
        <- lang_ru;;
    *);;
```

**Ключевые поля понятия:**
| Поле | Обязательность | Описание |
|------|---------------|----------|
| `<= nrel_inclusion: topic_xxx` | ✅ ОБЯЗАТЕЛЬНО | Привязка к теме |
| `<- concept` | ✅ ОБЯЗАТЕЛЬНО | Тип узла |
| `nrel_main_idtf` | ✅ ОБЯЗАТЕЛЬНО | Русское название |
| `nrel_definition` | ✅ ОБЯЗАТЕЛЬНО | Определение понятия |
| `nrel_explanation` | ✅ ОБЯЗАТЕЛЬНО | Пояснение |
| `nrel_example` | ⚡ Желательно | Пример использования |

---

#### Шаг 3: Привязать тему к дисциплине

В файле дисциплины добавить тему в `nrel_decomposition`:

```
topic_my_discipline
<- concept_discipline;
...
=> nrel_decomposition: <
    topic_existing_topic;
    topic_my_topic          ← новая тема
>;;
```

---

### ⚠️ Частые ошибки

#### 1. Неправильный тип темы (САМАЯ ЧАСТАЯ!)

❌ Неправильно:
```
concept_sc_code_topic
<- sc_node_class;         ← НЕПРАВИЛЬНО!
```

✅ Правильно:
```
concept_sc_code_topic
<- concept_discipline_topic;   ← ПРАВИЛЬНО!
```

**Почему:** Продакшены бота ищут узлы типа `concept_discipline_topic`. Если тип другой — тема не находится и бот отвечает «Я не знаю такой темы».

#### 2. Инлайн-определение понятий вместо отдельных файлов

❌ Неправильно:
```
concept_sc_code_topic
<- concept_discipline_topic;
=> nrel_components:
   concept_sc_code
(*
=> nrel_main_idtf: [SC-код] ...
*);
```

✅ Правильно:
```
// В файле темы:
concept_sc_code_topic
<- concept_discipline_topic;
=> nrel_key_concepts: { concept_sc_code; ... };;

// В отдельном файле concept_sc_code.scs:
concept_sc_code
<= nrel_inclusion: concept_sc_code_topic;
<- concept;
=> nrel_main_idtf: [SC-код] ...
```

**Почему:** Шаблоны продакшенов ищут отдельные узлы со связями, а не инлайн-блоки внутри темы.

#### 3. Забыть `nrel_key_concepts` в теме

Без этого списка продакшен `@if_discipline_topic_information_found_production` не найдёт понятия темы.

#### 4. Забыть `<- concept` в файле понятия

Без этого понятие не будет распознано как concept и шаблоны его не найдут.

---

### 🔍 Как проверить, что тема работает

1. Отправьте боту название темы (например, «Основные понятия SC-кода»)
2. Бот должен ответить информацией из `nrel_explanation` темы (а не «Я не знаю такой темы»)
3. Если ответили «да» — бот должен показать перечень тем из `nrel_decomposition` дисциплины
4. Если ввели название понятия — бот должен найти его и показать `nrel_definition` + `nrel_explanation`

---

### 📁 Структура файлов (шаблон)

```
knowledge-base/
├── ostis_knowledge/
│   ├── topic_my_discipline.scs          ← дисциплина
│   ├── topic_my_topic.scs               ← тема
│   ├── concept_xxx.scs                  ← понятие 1
│   ├── concept_yyy.scs                  ← понятие 2
│   └── concept_zzz.scs                  ← понятие 3
```

Или для вложенных структур:
```
knowledge-base/
├── system/
│   └── disciplines/
│       └── my_discipline/
│           └── topics/
│               └── topic-my-topic/
│                   ├── topic_my_topic.scs
│                   └── concepts/
│                       ├── concept_xxx.scs
│                       ├── concept_yyy.scs
│                       └── concept_zzz.scs
```

---

### 📝 Готовый шаблон нового понятия (скопировать и заполнить)

```
concept_NAME
<= nrel_inclusion: TOPIC_NAME;
<- concept;
=> nrel_main_idtf:
    [НАЗВАНИЕ НА РУССКОМ]
    (*
        <- lang_ru;;
    *);;
=> nrel_definition:
    [ОПРЕДЕЛЕНИЕ — что это такое.]
    (*
        <- concept_definition;;
        <- lang_ru;;
    *);;
=> nrel_explanation:
    [ПОЯСНЕНИЕ — подробнее о значении и применении.]
    (*
        <- concept_explanation;;
        <- lang_ru;;
    *);;
```

### 📝 Готовый шаблон новой темы (скопировать и заполнить)

```
topic_NAME
<- concept_discipline_topic;
=> nrel_main_idtf:
    [НАЗВАНИЕ ТЕМЫ]
    (*
        <- lang_ru;;
    *);;
=> nrel_explanation:
    [ОПИСАНИЕ ТЕМЫ — что изучается в этой теме.]
    (*
        <- concept_explanation;;
    *);;
=> nrel_key_concepts: {
    concept_1;
    concept_2;
    concept_3
};;
```
