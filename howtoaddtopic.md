# Руководство по добавлению новых тем и понятий в базу знаний

> Этот документ описывает, как правильно добавлять новые учебные дисциплины, темы и понятия в базу знаний диалоговой системы «Ника», чтобы они автоматически обрабатывались агентом `TopicInfoAgent`.

---

## 1. Общая структура

База знаний находится в папке `knowledge-base/`. Основные разделы:

```
knowledge-base/
├── ostis_knowledge/              ← Дисциплина «Основы формализации на SC-коде»
│   ├── topic_basics_of_formalization.scs    ← корневая дисциплина
│   ├── concept_basic_concepts.scs           ← тема + понятия
│   ├── sc_syntax.scs                        ← тема
│   ├── concept_sc_syntax.scs                ← понятия синтаксиса
│   ├── concept_sc_external_representation.scs
│   └── concept_sc_idtrf.scs
│
├── system/
│   ├── disciplines/                          ← другие дисциплины
│   │   └── ai/                               ← пример: «Искусственный интеллект»
│   │       ├── topic_ai.scs                  ← корневая дисциплина
│   │       └── topics/
│   │           └── topic-1-ai-concepts/
│   │               ├── topic_1_ai_concepts.scs      ← тема
│   │               └── concepts/                     ← понятия темы
│   │                   ├── concept_intelligent_system.scs
│   │                   └── concept_knowledge_base.scs
│   ├── common/
│   │   └── concepts.scs                     ← базовые отношения (nrel_*, rrel_*)
│   └── nika.scs                             ← описание самой Ники
│
└── users/                                   ← пользователи и их классы
```

---

## 2. Как добавить новую дисциплину

Создайте файл дисциплины, например `knowledge-base/system/disciplines/my-subject/topic_my_subject.scs`:

```scs
topic_my_subject
<- concept_discipline;
=> nrel_main_idtf:
    [Моя дисциплина]
    (*
        <- lang_ru;;
    *);
=> nrel_definition:
    [Определение моей дисциплины — краткое описание её содержания.]
    (*
        <- concept_definition;;
    *);
=> nrel_explanation:
    [Развёрнутое пояснение — что изучается, для чего, какие задачи решает.]
    (*
        <- concept_explanation;;
    *);
=> nrel_decomposition: <
    topic_1_my_subject;
    topic_2_my_subject
>;
=> nrel_purpose:
    [Цели изучения дисциплины (знать/уметь/владеть).]
    (*
        <- concept_purpose;;
        => nrel_format: format_html;;
    *);;
```

**Важно:**
- `<- concept_discipline;` — обязательно (класс дисциплины)
- `=> nrel_decomposition: < ... >;` — связь с темами
- Каждый текстовый контент должен быть с `<- lang_ru;;`

---

## 3. Как добавить новую тему

Создайте файл темы, например `knowledge-base/system/disciplines/my-subject/topics/topic-1-my-subject/topic_1_my_subject.scs`:

```scs
topic_1_my_subject
<- concept_discipline_topic;
=> nrel_main_idtf:
    [Тема 1. Название темы]
    (*
        <- lang_ru;;
    *);
=> nrel_explanation:
    [Пояснение темы — что именно рассматривается, какие аспекты охвачены.]
    (*
        <- concept_explanation;;
    *);
=> nrel_key_concepts: {
    concept_my_first_concept;
    concept_my_second_concept
};;
```

**Важно:**
- `<- concept_discipline_topic;` — обязательно (класс темы)
- `=> nrel_explanation:` — пояснение, которое Ника покажет при запросе «что ты знаешь по теме ...»
- `=> nrel_key_concepts: { ... };` — список ключевых понятий темы (системные идентификаторы)

Затем добавьте тему в декомпозицию дисциплины (в файл дисциплины):
```scs
=> nrel_decomposition: <
    topic_1_my_subject;   // ← добавить сюда
    ...
>;
```

---

## 4. Как добавить новое понятие

Создайте файл понятия, например `knowledge-base/system/disciplines/my-subject/topics/topic-1-my-subject/concepts/concept_my_first_concept.scs`:

```scs
concept_my_first_concept
<- sc_node_class;
<- concept;
=> nrel_main_idtf:
    [моё первое понятие]
    (*
        <- lang_ru;;
    *);
=> nrel_definition:
    [Определение понятия — чёткое, краткое описание сущности.]
    (*
        <- concept_definition;;
    *);
=> nrel_explanation:
    [Пояснение понятия — более развёрнутое описание, примеры, контекст.]
    (*
        <- concept_explanation;;
    *);
=> nrel_example:
    [Пример использования понятия.]
    (*
        <- concept_example;;
    *);;
```

**Важно:**
- **Обязательно** добавьте `nrel_definition` и `nrel_explanation` — без них Ника не сможет ответить на вопрос «что такое ...»
- `nrel_example` — опционально, но полезно для понимания
- Имя файла должно совпадать с системным идентификатором (например `concept_my_first_concept.scs`)
- Все системные идентификаторы — только латиница, цифры и `_`
- Русский текст — только в контенте `[ ... ]` с пометкой `<- lang_ru;;`

---

## 5. Автоматическая обработка агентами

### Что делает TopicInfoAgent (Python):

| Запрос пользователя | Что ищет в БЗ | Какие данные выводит |
|---|---|---|
| «какие темы ты знаешь» | Все `concept_discipline_topic` | Названия тем |
| «что ты знаешь по теме X» | Тему по названию → `nrel_explanation` + `nrel_key_concepts` | Пояснение + список понятий |
| «какие темы есть по дисциплине Y» | Дисциплину → `nrel_decomposition` | Список тем |
| «расскажи про дисциплину Y» | Дисциплину → `nrel_definition`, `nrel_explanation`, `nrel_purpose` | Определение, описание, цель |
| «что такое Z» / «расскажи про понятие Z» | Понятие по `nrel_main_idtf` → `nrel_definition`, `nrel_explanation` | Определение + пояснение |
| «какие дисциплины ты знаешь» | Все `concept_discipline` | Названия дисциплин |

### Контекст диалога

TopicInfoAgent учитывает историю диалога:
- Если пользователь ранее спрашивал про дисциплину, при следующем запросе «расскажи про тему ...» поиск сначала ведётся в рамках этой дисциплины
- Это предотвращает попадание темы из другой дисциплины

---

## 6. Чек-лист при добавлении нового контента

- [ ] Системный идентификатор уникален во всей БЗ
- [ ] Имя файла = системный идентификатор (`.scs`)
- [ ] Файл добавлен в `repo.path` или поддиректорию, уже включённую в `repo.path`
- [ ] У всех понятий есть `nrel_definition` + `nrel_explanation`
- [ ] У всех тем есть `nrel_explanation` + `nrel_key_concepts`
- [ ] У всех дисциплин есть `nrel_definition` + `nrel_explanation` + `nrel_decomposition`
- [ ] Каждый текстовый контент с русским текстом помечен `<- lang_ru;;`
- [ ] Скобки сбалансированы: `{ }`, `< >`, `[ ]`, `(* *)`
- [ ] После сборки БЗ (`./scripts/start.sh build_kb`) и перезапуска Ника новый контент доступен для вопросов

---

## 7. Типовые ошибки

| Ошибка | Причина | Исправление |
|---|---|---|
| Ника не находит тему | Нет `<- concept_discipline_topic;` | Добавить класс темы |
| Ника не находит понятие | В `_find_concept_by_name` ищется по `nrel_main_idtf` | Проверить, что у понятия есть `nrel_main_idtf` |
| Нет пояснения в ответе | У понятия нет `nrel_explanation` | Добавить `nrel_explanation` |
| Ника отвечает не той темой | Контекст дисциплины не установлен или тема есть в другой дисциплине | Сначала спросить про дисциплину |
| Ошибка сборки БЗ | Несбалансированные скобки или кириллица в системном idtf | Проверить синтаксис SCs |

---

## 8. Пример: минимальный рабочий набор

Дисциплина + одна тема + одно понятие:

**Файл: `knowledge-base/system/disciplines/example/topic_example.scs`:**
```scs
topic_example
<- concept_discipline;
=> nrel_main_idtf: [Пример] (* <- lang_ru;; *);
=> nrel_definition: [Пример дисциплины.] (* <- concept_definition;; *);
=> nrel_decomposition: < topic_1_example >;;
```

**Файл: `knowledge-base/system/disciplines/example/topics/topic-1-example/topic_1_example.scs`:**
```scs
topic_1_example
<- concept_discipline_topic;
=> nrel_main_idtf: [Тема 1. Пример] (* <- lang_ru;; *);
=> nrel_explanation: [Пояснение темы.] (* <- concept_explanation;; *);
=> nrel_key_concepts: { concept_example_concept };;
```

**Файл: `knowledge-base/system/disciplines/example/topics/topic-1-example/concepts/concept_example_concept.scs`:**
```scs
concept_example_concept
<- sc_node_class;
<- concept;
=> nrel_main_idtf: [пример понятия] (* <- lang_ru;; *);
=> nrel_definition: [Определение.] (* <- concept_definition;; *);
=> nrel_explanation: [Пояснение.] (* <- concept_explanation;; *);;
```
