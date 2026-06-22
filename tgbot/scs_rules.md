# Правила написания SCs-кода (Nika / OSTIS)

## 1. Базовый синтаксис

### Коннекторы
| Символ | Тип связи | Значение |
|--------|-----------|----------|
| `<-` / `->` | принадлежность (членство) | «является элементом класса» |
| `<=` / `=>` | общая дуга (ориентированное отношение) | с `nrel_*` / `rrel_*` |

**Направление:** `a -> b` = «от a к b». `b <- a` эквивалентно `a -> b`.

### Окончания
- `;` — разделяет предложения **внутри** описания одного элемента.
- `;;` — **завершает** всё описание элемента. Последняя конструкция в файле всегда `;;`.
- Если поставить `;;` раньше времени — следующие конструкции останутся без субъекта (ошибка парсинга).

### Литералы
- Системный идентификатор: латиница, цифры, `_`. Например: `concept_student_message`.
- Контент (текст): в `[квадратных скобках]`. Может быть многострочным.
- Именованные алиасы: `@alias_name` в шаблонах продукций.
- Переменные узлы: `.._name` (постфикс `_`).
- Переменные дуги: `<-_`, `_=>`, `_->` (инфикс/постфикс `_`).
- Анонимный узел: `...` (описывается далее в контуре).
- Внутренний контур: `(* ... *)` — описывает свойства предыдущего элемента.
- Множества: `{ a; b; c }`.
- Кортежи (упорядоченные): `< a; b; c >` — порядок важен (соответствует `rrel_1`, `rrel_2`).

### Комментарии
```scs
// однострочный комментарий
```

## 2. Базовая структура понятия

```scs
concept_example_entity
<- sc_node_class;
<- concept;
=> nrel_main_idtf:
    [пример сущности]
    (*
        <- lang_ru;;
    *);
=> nrel_definition:
    [Определение понятия.]
    (*
        <- concept_definition;;
    *);
=> nrel_explanation:
    [Пояснение понятия.]
    (*
        <- concept_explanation;;
    *);;
```

Всегда добавляйте `<- lang_ru;;` к текстовым контентам на русском языке.

## 3. Структура темы сообщения (message topic)

```scs
concept_student_message_about_searching_X
<- sc_node_class;
=> nrel_main_idtf:
    [класс сообщений о ...]
    (*
        <- lang_ru;;
    *);
<- concept_message_topic;
<= nrel_inclusion: concept_student_message;
=> nrel_corresponding_skill:
    ...
    (*
        => nrel_main_idtf: [...]
            (* <- lang_ru;; *);;
        <- concept_skill;;
        <- .process_materials;;   // или .process_disciplines
    *);
=> nrel_reply_production_chain: <
    @if_X_found_production;
    @if_X_not_found_production
>;
=> nrel_message_keywords: [
    ключевое слово;
    другая фраза;
];
=> nrel_message_patterns: [];  // regex-шаблоны (могут быть пустыми)
=> nrel_entity_class_descriptions: {
    {
        rrel_entity_class: concept
    }
};;
```

## 4. Логические продукции (nrel_reply_production)

### Базовая структура

```scs
// Шаблон текста ответа
@xxx_reply_template = [Текст с ${подстановками}];;

// Продукция с условием (найдено)
@if_xxx_found_production = {
    rrel_condition_template: {
        rrel_template: [*
            @input_param1 = (.._entity <-_ concept_class);;
            .._entity _=> nrel_definition:: .._def;;
            .._def <-_ concept_definition;;
        *];
        rrel_template_input_params: { @input_param1 }
    } (* <- nrel_search_template;; *);
    rrel_reply_template: {
        rrel_message_template: @xxx_reply_template;
        rrel_message_template_params: < @param1; @param2 >;
        rrel_message_class: concept_system_reply_message;
    }
};;
@if_xxx_found_production <- nrel_reply_production;;

// Продукция без условия (fallback — «не найдено»)
@if_xxx_not_found_production = {
    rrel_reply_template: {
        rrel_message_template: @not_found_reply
    }
};;
@if_xxx_not_found_production <- nrel_reply_production;;
```

### Правила для продукций
1. Самая специфичная продукция — первой в цепочке, fallback — последней.
2. Для fallback-продукции `rrel_condition_template` отсутствует (срабатывает безусловно).
3. `@xxx_production <- nrel_reply_production;;` — обязательно для каждой продукции.
4. Переменные дуги в шаблонах: `<-_`, `_=>`, `_->`, `::` (дуга к атрибуту тоже переменная).
5. `nrel_search_template` — простой поиск; `nrel_search_set_template` — множественный поиск.
6. `rrel_message_template_params: < @p1; @p2 >` — кортеж (порядок важен!), если шаблон использует `${1}`, `${2}`.

## 5. Подстановки в шаблонах ответа

- `${concept_definition}` — по системному имени найденной сущности.
- `${1}`, `${2}` — по позиции из `rrel_message_template_params`.
- HTML-разметка допускается (`<b>...</b>`) с `format_html`.
- `#foreach ... #endfor` — перебор множества; `#foreach#cwf ... #endfor#cwf` — вложенный.
- `${foreach.item.index}` — индекс текущего элемента.
- `#capitalize_first_letter(...)`, `#normalize(...)` — функции форматирования.

## 6. Частые отношения

### nrel_* (бинарные отношения)
| Отношение | Назначение |
|-----------|-----------|
| `nrel_main_idtf` | основной идентификатор (имя для пользователя) |
| `nrel_definition` | определение |
| `nrel_explanation` | пояснение |
| `nrel_purpose` | назначение / цель |
| `nrel_example` | пример |
| `nrel_note` | примечание |
| `nrel_inclusion` | включение в надкласс |
| `nrel_decomposition` | декомпозиция на подэлементы |
| `nrel_key_concepts` | ключевые понятия темы |
| `nrel_reply_production` | класс логических продукций |
| `nrel_reply_production_chain` | цепочка продукций (кортеж) |
| `nrel_corresponding_skill` | навык для темы сообщения |
| `nrel_message_keywords` | ключевые фразы для классификации |
| `nrel_message_patterns` | regex-шаблоны |
| `nrel_entity_class_descriptions` | какие сущности извлекать из сообщения |
| `nrel_greeted_user` | флаг «пользователь поприветствован» |
| `nrel_known_user` | флаг «пользователь известен системе» |
| `nrel_user_id` | Telegram ID пользователя |
| `nrel_message_author` | автор сообщения |
| `nrel_reply_to_message` | связь ответа с исходным сообщением |

### rrel_* (ролевые отношения)
- `rrel_condition_template` — условие продукции (часть «ЕСЛИ»)
- `rrel_reply_template` — шаблон ответа (часть «ТО»)
- `rrel_template` — sc-шаблон поиска
- `rrel_template_input_params` — входные параметры шаблона
- `rrel_message_template` — алиас текста ответа
- `rrel_message_template_params` — параметры подстановки (кортеж)
- `rrel_message_class` — класс сообщения
- `rrel_entity_class` — класс извлекаемой сущности

## 7. Типовые ошибки

| Ошибка | Причина |
|--------|---------|
| `extraneous input '<='` | Элемент закрыт раньше времени — внутри используется `;;` вместо `;` |
| Понятие не находится | Нет `<- concept;` или нет `nrel_main_idtf` |
| Продукция не срабатывает | Неправильный порядок в цепочке, или отсутствует `<- nrel_reply_production;;` |
| Кириллица в системном idtf | Только латиница, цифры и `_` |
| Несбалансированные скобки | Пропущена `}` или `)` в контурах/множествах |

## 8. Соглашения об именовании

- Узлы-понятия: `concept_<имя>` (snake_case, латиница).
- Отношения: `nrel_<имя>` (некатегориальные), `rrel_<имя>` (ролевые).
- Навыки: с точкой-префиксом — `.process_disciplines`, `.help_students`.
- Алиасы продукций: `@if_<условие>_production`.
- Шаблоны ответов: `@<имя>_reply_template`.
- Системный субъект: `myself` (узел самой Ники).
