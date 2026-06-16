# Правила написания SCs‑кода и логических продукций (OSTIS / Nika)

> Документ‑справочник для нейросетей и разработчиков, дополняющих базу знаний проекта **OSTIS‑Telegram‑Assistant** (диалоговая система «Ника»). Описывает синтаксис языка **SCs** (внешнее представление SC‑кода) и шаблон **логических продукций** (`nrel_reply_production`), используемый для генерации ответов ассистента.

---

## 1. Базовый синтаксис SCs

SCs (SC‑code string) — текстовое представление семантической сети. Граф состоит из **узлов** и **связей (дуг/рёбер)**, выражаемых тройками `субъект — коннектор — объект`.

### 1.1. Завершение конструкций

- Одиночное `;` разделяет **предложения внутри одного описания** одного элемента.
- Двойное `;;` **завершает всё описание** элемента (предложение верхнего уровня).
- Каждый файл, как правило, заканчивается на `;;`.

```scs
concept_user
<- sc_node_class;
=> nrel_main_idtf:
    [пользователь]
    (*
        <- lang_ru;;
    *);;
```

### 1.2. Коннекторы (связки)

| Коннектор | Тип связи | Значение |
|-----------|-----------|----------|
| `<-` / `->` | принадлежность (членство) | «является элементом класса» (`элемент <- класс`) |
| `<=` / `=>` | ориентированное отношение (общая дуга) | используется с именованными отношениями `nrel_*` / `rrel_*` |
| `<=>` / `~>` и т.п. | прочие типы дуг | редко в этом проекте |
| `_` (постфикс/префикс) | **переменная** | дуга/узел является переменным в шаблоне (`<-_`, `_=>`, `.._x`) |

Направление: `a -> b` читается «от a к b». `b <- a` эквивалентно `a -> b`.

### 1.3. Литералы и идентификаторы

- **Системный идентификатор**: латиница, цифры, `_`. Пример: `concept_student_message`.
- **Содержимое (контент)**: в квадратных скобках `[ ... ]`. Может быть многострочным.
  ```scs
  [Решатель задач - компонент интеллектуальной системы.]
  ```
- **Множества**: фигурные скобки `{ a; b; c }`.
- **Кортежи (упорядоченные)**: угловые скобки `< a; b; c >` (порядок важен — соответствует `rrel_1`, `rrel_2`, ...).
- **Внутренний контур / вложенное описание узла**: `(* ... *)` — описывает свойства предшествующего элемента.
- **Анонимный узел**: `...` (безымянный sc‑элемент, описываемый далее в контуре `(* *)`).

### 1.4. Описание свойств через внутренний контур `(* *)`

Внутри `(* *)` описывают атрибуты только что упомянутого элемента:

```scs
=> nrel_main_idtf:
    [найти информацию по дисциплине]
    (*
        <- lang_ru;;          // контент относится к русскому языку
    *);
```

### 1.5. Переменные (для шаблонов)

- `.._x` — **переменный sc‑узел** (имя начинается с `.._`).
- `@x` — **именованный псевдоним/алиас** (template alias), на который можно ссылаться повторно.
- Постфикс/инфикс `_` у коннектора (`<-_`, `_=>`, `_->`) делает **дугу переменной** — обязательно в шаблонах поиска/генерации.

### 1.6. Комментарии

```scs
// однострочный комментарий
//////////////////////////////
// блок-заголовок секции
//////////////////////////////
```

---

## 2. Типовые отношения и классы проекта

### 2.1. Базовые классы узлов

- `sc_node_class` — узел является **классом**.
- `concept`, `concept_class` — понятие/класс понятий.
- `concept_binary_relation`, `concept_quasibinary_relation` — типы отношений.
- `concept_message_topic` — класс «тема сообщения» (см. §4).

### 2.2. Частые `nrel_*` (бинарные отношения «n‑relation»)

| Отношение | Назначение |
|-----------|-----------|
| `nrel_main_idtf` | основной идентификатор (имя для пользователя), обычно с `<- lang_ru` |
| `nrel_definition` | определение (`<- concept_definition`) |
| `nrel_explanation` / `nrel_simple_explanation` | объяснение (`<- concept_explanation`) |
| `nrel_note` | примечание (`<- concept_note`) |
| `nrel_purpose` | назначение (`<- concept_purpose`) |
| `nrel_example` | пример (`<- concept_example`) |
| `nrel_inclusion` | включение класса в надкласс (`child <= nrel_inclusion: parent`) |
| `nrel_key_concepts` | ключевые понятия темы |
| `nrel_format` | формат контента (например `format_html`) |
| `nrel_reply_production` | **класс логических продукций** (см. §3) |
| `nrel_reply_production_chain` | упорядоченная цепочка продукций (кортеж `< >`) |
| `nrel_corresponding_skill` | соответствующий навык темы сообщения |
| `nrel_message_keywords` / `nrel_message_patterns` | ключевые слова/шаблоны для классификации сообщений |
| `nrel_entity_class_descriptions` | какие сущности извлекать из сообщения |
| `nrel_greeted_user` / `nrel_known_user` | служебные отношения о состоянии пользователя |

### 2.3. Частые `rrel_*` (ролевые отношения «role‑relation»)

Используются внутри структуры продукции (см. §3): `rrel_condition_template`, `rrel_reply_template`, `rrel_template`, `rrel_template_input_params`, `rrel_message_template`, `rrel_message_class`, `rrel_reply_message_class`, `rrel_context_message_class`, `rrel_entity_class`, и т.д.

### 2.4. Соглашения об именовании

- Узлы‑понятия: `concept_<имя>` (snake_case, латиница).
- Отношения: `nrel_<имя>` (некатегориальные), `rrel_<имя>` (ролевые).
- Навыки системы: с точкой‑префиксом — `.process_disciplines`, `.help_students`.
- Алиасы продукций: `@if_<условие>_production`, шаблоны ответов: `@<имя>_reply_template`.
- Системный субъект ассистента: **`myself`** (узел самой Ники).

---

## 3. Логические продукции (`nrel_reply_production`)

Продукция — это правило «**ЕСЛИ** (условие в БЗ выполняется) **ТО** (сформировать ответ/выполнить генерацию)». Это реализация продукционной модели представления знаний.

### 3.1. Структура одной продукции

```scs
// 1) Шаблон текста ответа (алиас)
@xxx_reply_template = [Текст ответа с подстановками ${concept_definition}];;

// 2) Сама продукция
@if_xxx_production = {
    rrel_condition_template: {
        rrel_template: [*
            @input_param1 = (.._concept <-_ concept_discipline);;
            .._concept _=> nrel_definition:: .._definition;;
            .._definition <-_ concept_definition;;
        *];
        rrel_template_input_params: {
            @input_param1
        }
    } (* <- nrel_search_template;; *);
    rrel_reply_template: {
        rrel_message_template: @xxx_reply_template;
        rrel_message_class: concept_system_reply_message_with_question;
        rrel_expected_user_reply_message_classes: {
            {
                rrel_reply_message_class: concept_student_positive_reply_message;
                rrel_context_message_class: concept_student_message_about_searching_concepts
            }
        }
    }
};;

// 3) Отнесение к классу продукций
@if_xxx_production <- nrel_reply_production;;
```

### 3.2. Часть «ЕСЛИ» — `rrel_condition_template`

- Содержит `rrel_template: [* ... *]` — **sc‑шаблон поиска** в базе знаний (внутри `[* *]`).
- Внутри шаблона все дуги — **переменные** (постфикс `_`): `<-_`, `_=>`, `_->`.
- `::` после отношения (`_=> nrel_definition:: .._definition`) означает, что **дуга к атрибуту тоже переменная**.
- `rrel_template_input_params` — множество входных параметров (например, `@input_param1` — сущность, извлечённая из сообщения пользователя).
- Контур `(* <- nrel_search_template;; *)` помечает тип шаблона:
  - `nrel_search_template` — простой поиск одной конструкции;
  - `nrel_search_set_template` — поиск множества (множественные совпадения);
  - `nrel_generate_template` — генерация (запись) новой конструкции в БЗ (часть «ТО» как действие, без текста);
  - `nrel_fixed_search_strategy_template` — составная стратегия поиска (см. §3.5).

**Если `rrel_condition_template` отсутствует** — продукция срабатывает безусловно (используется как fallback «не найдено», ставится последней в цепочке).

### 3.3. Часть «ТО» — `rrel_reply_template`

- `rrel_message_template` — алиас шаблона текста ответа.
- `rrel_message_template_params: < @p1; @p2; @p3 >` — **кортеж** параметров для подстановки `${1}`, `${2}`, `${3}` (порядок важен).
- `rrel_message_class` — класс формируемого сообщения системы (например `concept_system_reply_message_with_question`).
- `rrel_expected_user_reply_message_classes` — множество ожидаемых ответов пользователя; каждый элемент:
  - `rrel_reply_message_class` — какой класс ответа ожидаем (положительный/отрицательный/неизвестный);
  - `rrel_context_message_class` — в какую тему перейти при таком ответе (контекст диалога).

### 3.4. Шаблоны текста ответа

В `[ ... ]` поддерживаются подстановки и директивы шаблонизатора:

- `${concept_definition}` — подстановка по системному имени найденной сущности/класса.
- `${1}`, `${2}`, `${3}` — подстановка по позиции из `rrel_message_template_params`.
- `${concept_student}`, `${concept_intelligent_system}` — подстановка имени сущности диалога.
- HTML‑разметка допускается: `<b>...</b>` (формат `format_html`).
- Директивы цикла/форматирования:
  - `#foreach ... #endfor` — перебор множества; вложенный `#foreach#cwf ... #endfor#cwf`.
  - `${foreach.item.index}` — индекс текущего элемента.
  - `#capitalize_first_letter(...)`, `#normalize(...)` — функции форматирования.

### 3.5. Составные стратегии поиска (`nrel_fixed_search_strategy_template`)

Для многошагового поиска используется связка `rrel_init_template` + `rrel_next_template`:

```scs
rrel_condition_template: {
    rrel_init_template: {
        rrel_template: [* ... @message_template_param1 = @input_param1;; *];
        rrel_template_input_params: { @input_param1 }
    } (* <- nrel_search_set_template;; *);
    rrel_next_template: {
        rrel_init_template: {
            rrel_template: [* ... *];
            rrel_sort_param: @sort_param;
            rrel_template_input_params: { @input_param1 }
        } (* <- nrel_search_set_template;; *)
    } (* <- nrel_fixed_search_strategy_template;; *)
} (* <- nrel_fixed_search_strategy_template;; *);
```

- `rrel_sort_param` — параметр сортировки результатов (например `basic_specification_objects_order`).
- `rrel_template_output_params` — выходные параметры, передаваемые в следующий шаг.
- `@message_template_paramN` — алиасы, которые затем перечисляются в `rrel_message_template_params`.

---

## 4. Класс «тема сообщения» (`concept_message_topic`)

Каждое пользовательское намерение описывается отдельным классом сообщений. Каноническая структура файла‑темы:

```scs
concept_student_message_about_searching_concept_information
<- sc_node_class;
=> nrel_main_idtf:
    [класс сообщений учащихся о запросе определения понятия]
    (*
        <- lang_ru;;
    *);
<- concept_message_topic;
<= nrel_inclusion:
    concept_student_message;
=> nrel_corresponding_skill:
    ...
    (*
        => nrel_main_idtf:
            [объяснить указанное понятие]
            (*
                <- lang_ru;;
            *);;
        <- concept_skill;;
        <- .process_materials;;
    *);
=> nrel_example:
    [Что такое интеллектуальная система?]
    (*
        <- concept_example;;
    *);
=> nrel_reply_production_chain: <
    @if_concept_definition_found_production;
    @if_concept_information_not_found_production;
    @if_concept_not_found_production
>;
=> nrel_message_keywords: [
    что такое;
    что это;
    что значит;
];
=> nrel_message_patterns: [
];
=> nrel_entity_class_descriptions: {
    {
        rrel_entity_class: concept
    }
};;
```

### 4.1. Ключевые поля темы

- `<- concept_message_topic;` — относит класс к темам сообщений (обязательно).
- `<= nrel_inclusion: concept_student_message;` — родительский класс сообщений (учащиеся / неизвестные пользователи / система).
- `=> nrel_reply_production_chain: < ... >;` — **упорядоченная цепочка** продукций. Порядок определяет приоритет: система пробует продукции сверху вниз и применяет **первую**, чьё условие выполнено.
- `=> nrel_corresponding_skill: ...` — навык системы, к которому относится тема (привязка к `.process_*`).
- `=> nrel_message_keywords: [ ... ]` — ключевые фразы для классификации сообщения (через `;`).
- `=> nrel_message_patterns: [ ... ]` — шаблоны/регэкспы (могут быть пустыми).
- `=> nrel_entity_class_descriptions: { { rrel_entity_class: <класс> } }` — какие сущности извлекать из текста (становятся входными параметрами продукций).

### 4.2. Порядок продукций в цепочке (важно!)

Располагайте от **самой специфичной** к **самой общей**:

1. Полное совпадение (найдены все данные) → подробный ответ.
2. Частичное совпадение → краткий ответ.
3. Сущность найдена, но данных нет → «мало информации».
4. Сущность вообще не найдена (без `rrel_condition_template`) → «не знаю такого».

---

## 5. Чек‑лист при добавлении нового файла

1. **Имя файла = имя главного узла** (например `concept_student_message_about_X.scs`).
2. Завершайте описания `;;`, предложения внутри — `;`.
3. У всех контентов‑имён добавляйте `(* <- lang_ru;; *)`.
4. Для шаблонов поиска используйте **переменные** (`.._x`, `<-_`, `_=>`, `::`).
5. Каждую продукцию заканчивайте строкой `@xxx_production <- nrel_reply_production;;`.
6. Перечислите все продукции в `nrel_reply_production_chain` в правильном порядке.
7. Обязательно добавьте fallback‑продукцию «не найдено» в конце цепочки.
8. Новые ссылки (`concept_*`, `nrel_*`) должны существовать в БЗ или быть объявлены.
9. Проверьте парность скобок: `{ }`, `< >`, `[ ]`, `[* *]`, `(* *)`.
10. Не используйте кириллицу в системных идентификаторах — только в контенте `[ ... ]`.

---

## 6. Минимальные шаблоны для копирования

### 6.1. Простое понятие

```scs
concept_example_entity
<- sc_node_class;
=> nrel_main_idtf:
    [пример сущности]
    (*
        <- lang_ru;;
    *);
=> nrel_definition:
    [Определение примера сущности.]
    (*
        <- concept_definition;;
    *);;
```

### 6.2. Продукция «найдено» + «не найдено»

```scs
@found_reply = [✅ Нашёл: ${concept_definition}];;

@if_found_production = {
    rrel_condition_template: {
        rrel_template: [*
            @input_param1 = (.._x <-_ concept_example_entity);;
            .._x _=> nrel_definition:: .._def;;
            .._def <-_ concept_definition;;
        *];
        rrel_template_input_params: { @input_param1 }
    } (* <- nrel_search_template;; *);
    rrel_reply_template: {
        rrel_message_template: @found_reply
    }
};;
@if_found_production <- nrel_reply_production;;

@not_found_reply = [🔍 Ничего не нашёл по запросу.];;

@if_not_found_production = {
    rrel_reply_template: {
        rrel_message_template: @not_found_reply
    }
};;
@if_not_found_production <- nrel_reply_production;;
```

### 6.3. Тема сообщения, связывающая продукции

```scs
concept_example_message_topic
<- sc_node_class;
=> nrel_main_idtf:
    [класс сообщений о примере]
    (*
        <- lang_ru;;
    *);
<- concept_message_topic;
<= nrel_inclusion:
    concept_student_message;
=> nrel_reply_production_chain: <
    @if_found_production;
    @if_not_found_production
>;
=> nrel_message_keywords: [
    пример;
    покажи пример
];
=> nrel_message_patterns: [
];
=> nrel_entity_class_descriptions: {
    {
        rrel_entity_class: concept_example_entity
    }
};;
```

---

> **Источник правил:** структура реальных файлов БЗ в `knowledge-base/` проекта (Nika). При сомнениях сверяйтесь с существующими примерами в `knowledge-base/system/messages/known-user-messages/student-messages/examples/`.
