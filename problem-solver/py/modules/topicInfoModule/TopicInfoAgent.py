import logging
import re
from sc_client.models import ScAddr, ScTemplate
from sc_client.constants import sc_type
from sc_client.client import search_by_template

from sc_kpm import ScAgentClassic, ScResult
from sc_kpm.sc_sets import ScOrientedSet
from sc_kpm.utils import (
    get_link_content_data,
    get_element_system_identifier,
    generate_link,
    generate_non_role_relation,
    search_element_by_non_role_relation,
)
from sc_kpm.utils.action_utils import (
    get_action_arguments,
    finish_action_with_status,
)
from sc_kpm import ScKeynodes

from modules.messageClassifyModule.classifier.MessageClassifier import MessageClassifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(message)s",
    datefmt="[%d-%b-%y %H:%M:%S]",
)


class TopicInfoAgent(ScAgentClassic):
    """
    Агент для обработки запросов о темах, дисциплинах и понятиях.
    Получает сообщение, классифицирует его, и для соответствующих запросов
    ищет информацию в базе знаний и генерирует ответ.
    Учитывает контекст предыдущих сообщений (какая дисциплина обсуждалась).
    """

    _MIN_NAME_LENGTH = 3

    def __init__(self):
        super().__init__("message_topic_info_action")
        self.classifier = MessageClassifier()
        self.logger = logging.getLogger(__name__)
        # Словарь тестов (шаблоны _TEST_DAY_1..7 объявлены ниже)
        self._TEST_TEMPLATES = {
            1: self._TEST_DAY_1,
            2: self._TEST_DAY_2,
            3: self._TEST_DAY_3,
            4: self._TEST_DAY_4,
            5: self._TEST_DAY_5,
            6: self._TEST_DAY_6,
            7: self._TEST_DAY_7,
        }
        # Правильные ответы для тестов: [ответ_на_в1, ответ_на_в2, ...]
        self._TEST_CORRECT_ANSWERS = {
            1: [2, 2, 2, 2, 2],  # День 1: Философия и архитектура OSTIS
            2: [2, 3, 1, 2, 2],  # День 2: Анатомия SC-кода
            3: [2, 3, 2, 2, 2],  # День 3: От конструкций к знаниям
            4: [2, 2, 2, 1, 2],  # День 4: Синтаксис Ядра — Алфавит и SC-узлы
            5: [2, 2, 2, 2, 2],  # День 5: Синтаксис Ядра — SC-коннекторы
            6: [2, 2, 2, 2, 2],  # День 6: Идентификаторы и языки
            7: [2, 2, 2, 2, 2],  # День 7: Практикум формализации
        }

    def on_event(self, _1: ScAddr, _2: ScAddr, action_addr: ScAddr) -> ScResult:
        """Основной обработчик события"""
        self.logger.info("TopicInfoAgent: Started processing action")

        try:
            [arc_to_message_addr] = get_action_arguments(action_addr, 1)
        except Exception:
            self.logger.error("TopicInfoAgent: Failed to get action arguments")
            finish_action_with_status(action_addr, is_success=False)
            return ScResult.SKIP

        message_link_addr = self._get_message_link(arc_to_message_addr)
        if not message_link_addr.is_valid():
            self.logger.error("TopicInfoAgent: Message link not found")
            finish_action_with_status(action_addr, is_success=False)
            return ScResult.SKIP

        message = get_link_content_data(message_link_addr)
        self.logger.info(f"TopicInfoAgent: Message: {message}")

        message_author_class_addr = self._get_message_author_class(message_link_addr)
        if not message_author_class_addr.is_valid():
            self.logger.error("TopicInfoAgent: Author class not found")
            finish_action_with_status(action_addr, is_success=False)
            return ScResult.SKIP
        message_author_class = get_element_system_identifier(message_author_class_addr)

        message_history = self._get_user_dialogue_messages(arc_to_message_addr)

        message_topic_class, message_entities, _ = self.classifier.classify(
            message, message_author_class, message_history
        )
        self.logger.info(
            f"TopicInfoAgent: Classified as: {message_topic_class}, entities: {message_entities}"
        )

        reply_text = self._generate_reply(message_topic_class, message_entities, message_history, message)

        if reply_text:
            self._send_reply(message_link_addr, reply_text)
            self.logger.info(f"TopicInfoAgent: Reply sent: {reply_text[:100]}...")
            finish_action_with_status(action_addr, is_success=True)
            return ScResult.OK
        else:
            # Python-обработчик не может ответить на этот класс сообщения
            # (greeting, casual, skills, help, etc.) — пропускаем,
            # чтобы C++ Nika продукции обработали action
            self.logger.info(
                f"TopicInfoAgent: No Python handler for {message_topic_class}, skipping for Nika"
            )
            return ScResult.SKIP


    def _generate_reply(self, message_class: str, entities: dict, message_history: list[str] = None, message: str = None) -> str | None:
        """Генерирует ответ в зависимости от класса сообщения"""
        if message_class == "concept_student_message_about_searching_all_topics":
            return self._handle_all_topics()
        elif message_class == "concept_student_message_about_searching_concepts":
            return self._handle_all_concepts()
        elif message_class == "concept_student_message_about_searching_discipline_topic_information":
            topic_name = entities.get("concept_discipline_topic", "")
            return self._handle_topic_information(topic_name, message_history)
        elif message_class == "concept_student_message_about_searching_discipline_topics":
            discipline_name = entities.get("concept_discipline", "")
            return self._handle_discipline_topics(discipline_name)
        elif message_class == "concept_student_message_about_searching_discipline_information":
            discipline_name = entities.get("concept_discipline", "")
            return self._handle_discipline_information(discipline_name)
        elif message_class == "concept_student_message_about_searching_concept_information":
            concept_name = entities.get("concept", "")
            return self._handle_concept_information(concept_name, message_history)
        elif message_class == "concept_unknown_message":
            # Пробуем найти тему или понятие по тексту сообщения
            return self._handle_unknown_as_topic(message, message_history)
        return None


    def _handle_all_topics(self) -> str:
        """Список всех тем"""
        topic_names = self._find_all_topic_names()
        if not topic_names:
            return "Я пока не знаю никаких тем."
        topics_str = "\n".join([f"• {name}" for name in topic_names])
        return (
            f"Вот темы, которые я знаю:\n{topics_str}\n\n"
            f"Чтобы узнать подробнее, спроси «что ты знаешь по теме <название>»."
        )

    def _handle_all_concepts(self) -> str:
        """Список всех понятий, сгруппированных по темам"""
        # Собираем все темы с их ключевыми понятиями
        template = ScTemplate()
        template.triple(
            ScKeynodes["concept_discipline_topic"],
            sc_type.VAR_POS_ARC,
            sc_type.VAR_NODE >> "topic"
        )
        results = search_by_template(template)

        if not results:
            return "Я пока не знаю никаких понятий."

        topic_blocks = []
        total_concepts = 0

        for r in results:
            topic_addr = r.get("topic")
            topic_name = self._get_main_idtf(topic_addr)
            if not topic_name:
                continue

            concept_names = self._get_key_concepts_names(topic_addr)
            if not concept_names:
                continue

            total_concepts += len(concept_names)
            concepts_str = "\n".join([f"  • {name}" for name in concept_names])
            topic_blocks.append(f"📌 {topic_name}:\n{concepts_str}")

        if not topic_blocks:
            return "Я пока не знаю никаких понятий."

        # Сортируем блоки тем по алфавиту
        topic_blocks.sort()

        header = f"📚 Вот понятия, которые я знаю (всего {total_concepts}):\n"
        body = "\n\n".join(topic_blocks)
        footer = (
            "\n\nЧтобы узнать подробнее о понятии, спроси "
            "«что такое <название понятия>» или «расскажи про <понятие>»."
        )
        return header + body + footer

    def _handle_topic_information(self, topic_name: str, message_history: list[str] = None) -> str:
        """Информация по теме — с учётом контекста дисциплины из истории"""
        if not topic_name or len(topic_name.strip()) < self._MIN_NAME_LENGTH:
            return "По какой теме вы хотите получить информацию? Уточните название."

        context_discipline_addr = ScAddr()
        if message_history:
            context_discipline_addr = self._detect_context_discipline(message_history)

        topic_addr = self._find_topic_with_context(topic_name, context_discipline_addr)

        if not topic_addr or not topic_addr.is_valid():
            concept_result = self._handle_concept_information(topic_name, message_history)
            if concept_result and concept_result.startswith("\U0001f4a1"):
                return concept_result
            return (
                f"Тема «{topic_name}» мне не известна. "
                f"Попробуйте спросить «какие темы ты знаешь», чтобы увидеть все темы."
            )

        self.logger.info(f"TopicInfoAgent: Found topic addr: {topic_addr.value}")

        explanation = self._find_topic_explanation(topic_addr)
        self.logger.info(f"TopicInfoAgent: Got explanation: {explanation[:80] if explanation else 'EMPTY'}")

        concepts_list = self._get_key_concepts_names(topic_addr)
        concepts_str = ""
        if concepts_list:
            concepts_str = "\n".join([f"  \u2022 {name}" for name in concepts_list])

        parts = [f"\U0001f4da \u0422\u0435\u043c\u0430: {topic_name}"]
        if explanation:
            parts.append(f"\n{explanation}")
        if concepts_str:
            parts.append(f"\n\n\u041a\u043b\u044e\u0447\u0435\u0432\u044b\u0435 \u043f\u043e\u043d\u044f\u0442\u0438\u044f:\n{concepts_str}")
        return "\n".join(parts)

    def _find_topic_explanation(self, topic_addr: ScAddr) -> str:
        """Ищет пояснение темы"""
        return self._find_relation_link(topic_addr, "nrel_explanation")

    def _handle_discipline_topics(self, discipline_name: str) -> str:
        """Темы по дисциплине"""
        if not discipline_name or len(discipline_name.strip()) < self._MIN_NAME_LENGTH:
            return "По какой дисциплине вы хотите узнать темы? Уточните название."

        discipline_addr = self._find_entity_by_name("concept_discipline", discipline_name)
        if not discipline_addr or not discipline_addr.is_valid():
            return f"Дисциплина «{discipline_name}» мне не известна."

        topic_names = self._get_decomposition_names(discipline_addr)
        if not topic_names:
            return f"По дисциплине «{discipline_name}» пока нет тем."

        topics_str = "\n".join([f"\u2022 {name}" for name in topic_names])
        return (
            f"По дисциплине «{discipline_name}» есть следующие темы:\n{topics_str}\n\n"
            f"Чтобы узнать подробнее, спроси «что ты знаешь по теме <название>»."
        )

    def _handle_discipline_information(self, discipline_name: str) -> str:
        """Подробная информация по дисциплине"""
        if not discipline_name or len(discipline_name.strip()) < self._MIN_NAME_LENGTH:
            return "Про какую дисциплину вы хотите узнать? Уточните название."

        discipline_addr = self._find_entity_by_name("concept_discipline", discipline_name)
        if not discipline_addr or not discipline_addr.is_valid():
            return f"Дисциплина «{discipline_name}» мне не известна."

        definition = self._find_relation_link(discipline_addr, "nrel_definition")
        explanation = self._find_relation_link(discipline_addr, "nrel_explanation")
        purpose = self._find_relation_link(discipline_addr, "nrel_purpose")
        topic_names = self._get_decomposition_names(discipline_addr)

        parts = [f"\U0001f4d6 \u0414\u0438\u0441\u0446\u0438\u043f\u043b\u0438\u043d\u0430: {discipline_name}"]
        if definition:
            parts.append(f"\n\n\u041e\u043f\u0440\u0435\u0434\u0435\u043b\u0435\u043d\u0438\u0435:\n{definition}")
        if explanation:
            parts.append(f"\n\n\u041e\u043f\u0438\u0441\u0430\u043d\u0438\u0435:\n{explanation}")
        if purpose:
            parts.append(f"\n\n\u0426\u0435\u043b\u044c \u0438\u0437\u0443\u0447\u0435\u043d\u0438\u044f:\n{purpose}")
        if topic_names:
            topics_str = "\n".join([f"\u2022 {name}" for name in topic_names])
            parts.append(f"\n\n\u0422\u0435\u043c\u044b \u0434\u0438\u0441\u0446\u0438\u043f\u043b\u0438\u043d\u044b:\n{topics_str}")
        return "\n".join(parts)

    _CONCEPT_RELATION_ORDER = [
        ("nrel_definition", "Определение"),
        ("nrel_explanation", "Пояснение"),
        ("nrel_purpose", "Цель"),
        ("nrel_specification", "Уточнение"),
        ("nrel_simple_explanation", "Простое пояснение"),
        ("nrel_rules", "Правила"),
        ("nrel_principles", "Принципы"),
        ("nrel_note", "Примечание"),
        ("nrel_example", "Пример"),
        ("nrel_advantages", "Преимущества"),
        ("nrel_disadvantages", "Недостатки"),
        ("nrel_application_areas", "Сферы применения"),
    ]

    def _handle_concept_information(self, concept_name: str, message_history: list[str] = None) -> str:
        """Информация по понятию — все доступные свойства (определение, пояснение, замечания и т.д.)"""
        if not concept_name or len(concept_name.strip()) < self._MIN_NAME_LENGTH:
            return "Какое понятие вас интересует? Уточните название."

        concept_addr = self._find_concept_by_name(concept_name)
        if not concept_addr or not concept_addr.is_valid():
            return f"Понятие «{concept_name}» мне не известно. Попробуйте спросить по-другому."

        self.logger.info(f"TopicInfoAgent: Found concept addr: {concept_addr.value}")

        parts = [f"\U0001f4a1 \u041f\u043e\u043d\u044f\u0442\u0438\u0435: {concept_name}"]
        found_any = False

        for relation_idtf, label in self._CONCEPT_RELATION_ORDER:
            value = self._find_relation_link(concept_addr, relation_idtf)
            if value:
                found_any = True
                self.logger.info(f"TopicInfoAgent: {relation_idtf}: {value[:60]}...")
                parts.append(f"\n\n<b>{label}:</b>\n{value}")

        if not found_any:
            parts.append(f"\n\n\u042f \u0437\u043d\u0430\u044e \u043f\u043e\u043d\u044f\u0442\u0438\u0435 «{concept_name}», \u043d\u043e \u043f\u043e\u043a\u0430 \u043d\u0435 \u0438\u043c\u0435\u044e \u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e\u0439 \u0438\u043d\u0444\u043e\u0440\u043c\u0430\u0446\u0438\u0438 \u043e \u043d\u0451\u043c.")

        parts.append(f"\n\nНадеюсь, это помогло разобраться в теме! 😊\n\n🤔 Если хочешь узнать что-то о связанном понятии, то напиши его мне.\n🔍 Если нужны примеры — напиши «давай примеры».")

        return "\n".join(parts)

    _TEST_DAY_1 = """📝 <b>Тест: День 1 — Философия и архитектура OSTIS</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> Из скольких ключевых компонентов состоит архитектура OSTIS?
1️⃣ 2
2️⃣ 3
3️⃣ 4
4️⃣ 5

<b>Вопрос 2:</b> Какая главная проблема современных гибридных интеллектуальных систем?
1️⃣ Они слишком быстрые
2️⃣ Они монолитны — сложны в модификации, компоненты почти невозможно повторно использовать
3️⃣ У них плохой пользовательский интерфейс
4️⃣ Они требуют слишком много памяти

<b>Вопрос 3:</b> Что означает принцип Plug & Play в контексте OSTIS?
1️⃣ Компоненты нужно подключать вручную
2️⃣ Любая модель может быть легко интегрирована без дополнительных затрат
3️⃣ Система сама выбирает нужные компоненты
4️⃣ Компоненты нельзя заменять

<b>Вопрос 4:</b> База знаний в архитектуре OSTIS — это:
1️⃣ Хранилище файлов на диске
2️⃣ Компонент, описывающий любые виды знаний, легко дополняется
3️⃣ Реляционная база данных
4️⃣ Набор текстовых документов

<b>Вопрос 5:</b> OSTIS — это технология с открытым исходным кодом для:
1️⃣ Только баз данных
2️⃣ Совместимых интеллектуальных систем нового поколения
3️⃣ Графических редакторов
4️⃣ Веб-разработки

💡 <i>Если сомневаешься в ответах — перечитай материалы Дня 1 командой «покажи День 1»</i>"""

    _TEST_DAY_2 = """📝 <b>Тест: День 2 — Анатомия SC-кода. Базовые элементы</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> SC-код (Semantic Computer Code) — это:
1️⃣ Язык программирования
2️⃣ Универсальный формальный язык смыслового представления знаний
3️⃣ Графический редактор
4️⃣ Система управления базами данных

<b>Вопрос 2:</b> Что является атомарной единицей SC-кода?
1️⃣ sc-конструкция
2️⃣ sc-множество
3️⃣ sc-элемент
4️⃣ sc-структура

<b>Вопрос 3:</b> Какая иерархия элементов SC-кода верна?
1️⃣ sc-элемент → sc-множество → sc-структура → sc-конструкция
2️⃣ sc-элемент → sc-конструкция → sc-множество → sc-структура
3️⃣ sc-конструкция → sc-элемент → sc-множество
4️⃣ sc-структура → sc-множество → sc-конструкция

<b>Вопрос 4:</b> sc-структура — это:
1️⃣ Множество sc-элементов
2️⃣ Множество sc-элементов со связками между ними
3️⃣ Один sc-элемент
4️⃣ Файл на диске

<b>Вопрос 5:</b> Каждый sc-элемент является обозначением:
1️⃣ Числа
2️⃣ Множества
3️⃣ Строки
4️⃣ Файла

💡 <i>Если сомневаешься в ответах — перечитай материалы Дня 2 командой «покажи День 2»</i>"""

    _TEST_DAY_3 = """📝 <b>Тест: День 3 — От конструкций к знаниям</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> sc-текст — это:
1️⃣ Строка символов в текстовом файле
2️⃣ Связная семантически корректная sc-структура
3️⃣ Набор несвязанных sc-элементов
4️⃣ Текстовый документ

<b>Вопрос 2:</b> Что НЕ является sc-конструкцией?
1️⃣ sc-элемент
2️⃣ sc-множество
3️⃣ Файл
4️⃣ sc-структура

<b>Вопрос 3:</b> sc-идентификатор — это:
1️⃣ Числовой адрес элемента в памяти
2️⃣ Файл, являющийся внешним именем sc-элемента
3️⃣ Язык программирования
4️⃣ Тип данных

<b>Вопрос 4:</b> Основной sc-идентификатор — это:
1️⃣ Случайное имя, присвоенное элементу
2️⃣ sc-идентификатор, взаимно однозначно соответствующий sc-элементу
3️⃣ Адрес элемента в оперативной памяти
4️⃣ Тип sc-элемента

<b>Вопрос 5:</b> Для чего нужны sc-идентификаторы системе?
1️⃣ Для внутренней работы и вычислений
2️⃣ Исключительно для обмена информацией с пользователями
3️⃣ Для хранения данных на диске
4️⃣ Для оптимизации запросов

💡 <i>Если сомневаешься в ответах — перечитай материалы Дня 3 командой «покажи День 3»</i>"""

    _TEST_DAY_4 = """📝 <b>Тест: День 4 — Синтаксис Ядра. Алфавит и SC-узлы</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> Сколько классов в Алфавите Ядра SC-кода?
1️⃣ 3
2️⃣ 5
3️⃣ 7
4️⃣ 10

<b>Вопрос 2:</b> На какие два типа делятся sc-узлы по типу?
1️⃣ Большие и маленькие
2️⃣ Не являющиеся знаком файла и являющиеся знаком файла
3️⃣ Постоянные и временные
4️⃣ Позитивные и негативные

<b>Вопрос 3:</b> По постоянству sc-узлы делятся на:
1️⃣ Большие и маленькие
2️⃣ Константные и переменные
3️⃣ Активные и пассивные
4️⃣ Явные и неявные

<b>Вопрос 4:</b> Синтаксическая классификация sc-элементов делит их на:
1️⃣ sc-узел и sc-коннектор
2️⃣ sc-множество и sc-структуру
3️⃣ sc-текст и sc-знание
4️⃣ sc-дугу и sc-ребро

<b>Вопрос 5:</b> sc-узел — это класс sc-элементов, представляющих:
1️⃣ Связи между элементами
2️⃣ Узлы SC-кода (обозначения множеств)
3️⃣ Файлы на диске
4️⃣ Внешние идентификаторы

💡 <i>Если сомневаешься в ответах — перечитай материалы Дня 4 командой «покажи День 4»</i>"""

    _TEST_DAY_5 = """📝 <b>Тест: День 5 — Синтаксис Ядра. SC-коннекторы</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> sc-коннекторы — это класс sc-элементов, представляющих:
1️⃣ Узлы SC-кода
2️⃣ Обозначения sc-пар (связок между элементами)
3️⃣ Файлы на диске
4️⃣ Внешние идентификаторы

<b>Вопрос 2:</b> sc-ребро — это:
1️⃣ Ориентированный коннектор
2️⃣ Неориентированный коннектор
3️⃣ Тип sc-узла
4️⃣ Тип идентификатора

<b>Вопрос 3:</b> Какие два основных вида sc-дуг по типу?
1️⃣ Явные и неявные
2️⃣ Общего вида и основного вида (принадлежности)
3️⃣ Большие и малые
4️⃣ Внешние и внутренние

<b>Вопрос 4:</b> Какие бывают типы модальности sc-дуг принадлежности?
1️⃣ Только позитивные
2️⃣ Позитивные, негативные и нечёткие (fuzzy)
3️⃣ Только негативные
4️⃣ Постоянные и временные

<b>Вопрос 5:</b> nrel_incidence — это:
1️⃣ Отношение принадлежности классу
2️⃣ Отношение инцидентности обозначений sc-пар с их элементами
3️⃣ Тип sc-узла
4️⃣ Один из видов идентификаторов

💡 <i>Если сомневаешься в ответах — перечитай материалы Дня 5 командой «покажи День 5»</i>"""

    _TEST_DAY_6 = """📝 <b>Тест: День 6 — Внешний мир. Идентификаторы и языки</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> Какие три формы внешнего представления SC-кода существуют?
1️⃣ HTML, CSS, JavaScript
2️⃣ SCg, SCs, SCn
3️⃣ XML, JSON, YAML
4️⃣ PNG, JPG, GIF

<b>Вопрос 2:</b> Системный sc-идентификатор уникален:
1️⃣ В рамках одного естественного языка
2️⃣ В рамках всей базы знаний Экосистемы OSTIS
3️⃣ Только в одном SCs-файле
4️⃣ Нигде не уникален

<b>Вопрос 3:</b> Простой sc-идентификатор:
1️⃣ Содержит идентификаторы других элементов
2️⃣ Не содержит идентификаторов других элементов
3️⃣ Всегда является строковым
4️⃣ Всегда является числовым

<b>Вопрос 4:</b> SCg-код — это:
1️⃣ Строковое (линейное) представление
2️⃣ Графическое представление в виде рисунков
3️⃣ Гипертекстовое представление
4️⃣ Программный код на Python

<b>Вопрос 5:</b> SCn-код — это представление, максимально приближенное к:
1️⃣ Машинному коду
2️⃣ Естественному языку
3️⃣ Графическим схемам
4️⃣ Числовым данным

💡 <i>Если сомневаешься в ответах — перечитай материалы Дня 6 командой «покажи День 6»</i>"""

    _TEST_DAY_7 = """📝 <b>Тест: День 7 — Практикум формализации и экосистема</b>

<i>Проверь свои знания! Выбери правильный ответ на каждый вопрос.</i>

<b>Вопрос 1:</b> Что входит в стек технологий OSTIS Platform?
1️⃣ Только sc-memory
2️⃣ sc-memory, Python API, TypeScript API, scp-machine, интерпретатор интерфейсов и другие
3️⃣ Только редактор базы знаний
4️⃣ Только плагин для VS Code

<b>Вопрос 2:</b> Системные sc-идентификаторы рекомендуется формировать на основе:
1️⃣ Русских слов
2️⃣ Англоязычных идентификаторов
3️⃣ Случайных символов
4️⃣ Только цифр

<b>Вопрос 3:</b> Алфавит системных sc-идентификаторов:
1️⃣ Включает пробелы и спецсимволы
2️⃣ Максимально упрощён — без пробелов и спецсимволов
3️⃣ Включает любые символы Unicode
4️⃣ Состоит только из цифр

<b>Вопрос 4:</b> OSTIS Standard — это:
1️⃣ Компилятор SC-кода
2️⃣ Стандарт технологии OSTIS
3️⃣ Язык программирования
4️⃣ Графический редактор

<b>Вопрос 5:</b> Итоговое упражнение интенсива:
1️⃣ Написать программу на Python
2️⃣ Декомпозиция предметной области на узлы, дуги принадлежности и идентификаторы
3️⃣ Установить и настроить OSTIS
4️⃣ Прочитать всю документацию

💡 <i>Поздравляю с завершением интенсива! 🚀 Если сомневаешься в ответах — перечитай материалы Дня 7 командой «покажи День 7»</i>"""

    # Паттерны для определения запросов к дням учебного плана и тестам
    _DAY_PATTERNS = [
        # negative lookbehind чтобы "тест день N" не считался днём
        r'(?<!тест\s?)\bдень\s*(1|2|3|4|5|6|7)\b',
        r'(?<!тест\s?)\b(1|2|3|4|5|6|7)\s*день\b',
        r'\bдень\s*(первый|второй|третий|четв[её]ртый|пятый|шестой|седьмой)\b',
        r'\b(первый|второй|третий|четв[её]ртый|пятый|шестой|седьмой)\s*день\b',
        r'(?<!тест\s?)\bday\s*(1|2|3|4|5|6|7)\b',
    ]

    _TEST_PATTERNS = [
        r'\bтест\s*день\s*(1|2|3|4|5|6|7)\b',
        r'\bтест\s*(1|2|3|4|5|6|7)\b',
        r'\bпроверк[ау]\s*день\s*(1|2|3|4|5|6|7)\b',
        r'\bпроверк[ау]\s*(1|2|3|4|5|6|7)\b',
        r'\bпроверь\s*день\s*(1|2|3|4|5|6|7)\b',
        r'\bпроверь\s*(1|2|3|4|5|6|7)\b',
        r'\btest\s*day\s*(1|2|3|4|5|6|7)\b',
        r'\btest\s*(1|2|3|4|5|6|7)\b',
    ]

    # Паттерн для определения ответов на тест: последовательность из 5 цифр (1-4)
    # через пробел, запятую или вместе. Пример: "2 2 1 4 3", "2,2,1,4,3", "22143"
    _ANSWER_PATTERN = re.compile(
        r'^[\s,\;]*([1-4])[\s,\;]+([1-4])[\s,\;]+([1-4])[\s,\;]+([1-4])[\s,\;]+([1-4])[\s,\;]*$'
    )

    @staticmethod
    def _matches_any_pattern(text: str, patterns: list[str]) -> bool:
        """Проверяет, соответствует ли текст хотя бы одному regex-паттерну"""
        text_lower = text.lower().strip()
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return True
        return False

    @staticmethod
    def _parse_test_day(text: str) -> int | None:
        """Извлекает номер дня из запроса на тест. Возвращает 1-7 или None."""
        text_lower = text.lower().strip()
        # Ищем число от 1 до 7
        m = re.search(
            r'(?:тест\s*(?:день\s*)?|проверк[ау]\s*(?:день\s*)?|проверь\s*(?:день\s*)?|test\s*(?:day\s*)?)(\d)',
            text_lower
        )
        if m:
            num = int(m.group(1))
            if 1 <= num <= 7:
                return num
        # Ищем словесные обозначения
        day_words = {
            'первый': 1, 'второй': 2, 'третий': 3,
            'четвёртый': 4, 'четвертый': 4,
            'пятый': 5, 'шестой': 6, 'седьмой': 7,
        }
        word_pat = '|'.join(day_words.keys())
        m = re.search(rf'(?:тест\s*(?:день\s*)?|проверк[ау]\s*(?:день\s*)?|проверь\s*(?:день\s*)?|test\s*(?:day\s*)?)({word_pat})\b', text_lower)
        if m:
            return day_words.get(m.group(1))
        return None

    def _handle_test_message(self, message: str) -> str | None:
        """
        Обрабатывает запрос на тест напрямую (минуя Nika C++).
        Возвращает текст теста или None, если день не распознан.
        """
        day = self._parse_test_day(message)
        if day is not None and day in self._TEST_TEMPLATES:
            self.logger.info(f"TopicInfoAgent: Handling test for day {day} directly in Python")
            return self._TEST_TEMPLATES[day]
        return None

    def _detect_last_test_day_from_history(self, message_history: list[str]) -> int | None:
        """
        Ищет в истории диалога последний запрошенный тест чтобы понять,
        какой тест проверять.
        Использует _parse_test_day на пользовательских сообщениях, так как
        _get_user_dialogue_messages отфильтровывает сообщения бота (myself).
        """
        if not message_history:
            return None
        for msg in reversed(message_history):
            day = self._parse_test_day(msg)
            if day is not None:
                return day
        return None

    def _handle_test_answers(self, message: str, message_history: list[str] = None) -> str | None:
        """
        Проверяет ответы пользователя на тест.
        Определяет номер теста из истории диалога, сравнивает ответы с правильными.
        """
        m = self._ANSWER_PATTERN.match(message.strip())
        if not m:
            return None

        user_answers = [int(m.group(i)) for i in range(1, 6)]

        # Определяем, какой тест проверять
        test_day = self._detect_last_test_day_from_history(message_history or [])
        if test_day is None:
            return (
                "❓ Не могу определить, какой тест вы проверяете.\n"
                "Сначала запросите тест командой «тест день N» или «тест N»."
            )

        if test_day not in self._TEST_CORRECT_ANSWERS:
            return f"❓ Тест для дня {test_day} мне не известен."

        correct = self._TEST_CORRECT_ANSWERS[test_day]
        day_name = {
            1: "Философия и архитектура OSTIS",
            2: "Анатомия SC-кода. Базовые элементы",
            3: "От конструкций к знаниям",
            4: "Синтаксис Ядра — Алфавит и SC-узлы",
            5: "Синтаксис Ядра — SC-коннекторы",
            6: "Внешний мир — Идентификаторы и языки",
            7: "Практикум формализации и экосистема",
        }.get(test_day, f"День {test_day}")

        result_parts = [f"📊 <b>Результаты теста: День {test_day} — {day_name}</b>\n"]
        correct_count = 0

        for i, (user_ans, corr_ans) in enumerate(zip(user_answers, correct), start=1):
            if user_ans == corr_ans:
                correct_count += 1
                result_parts.append(f"✅ <b>Вопрос {i}:</b> {user_ans} (верно)")
            else:
                result_parts.append(f"❌ <b>Вопрос {i}:</b> {user_ans} (правильный ответ: {corr_ans})")

        total = len(correct)
        percent = int(correct_count / total * 100)
        result_parts.append(f"\n<b>Итого:</b> {correct_count}/{total} — {percent}%")

        if percent == 100:
            result_parts.append("🎉 Отлично! Все ответы верны!")
        elif percent >= 80:
            result_parts.append("👍 Хороший результат! Есть над чем поработать.")
        elif percent >= 60:
            result_parts.append("📖 Стоит повторить материал Дня.")
        else:
            result_parts.append("🔄 Рекомендую внимательнее изучить материалы Дня и попробовать снова.")

        result_parts.append("\n💡 Чтобы повторить тест, напиши «тест день N» ещё раз.")
        return "\n".join(result_parts)

    def _handle_unknown_as_topic(self, message: str, message_history: list[str] = None) -> str | None:
        """
        Пытается найти тему или понятие по тексту сообщения.
        Используется, когда классификатор не распознал запрос.
        Делегирует существующим обработчикам _handle_topic_information и _handle_concept_information.

        Если запрос похож на "тест N" / "тест день N" — возвращает текст теста напрямую
        (минуя Nika C++, чтобы избежать конфликта с ключевым словом "день N" из учебного плана).
        Если запрос похож на "день N" (без "тест") — возвращает None,
        чтобы Nika C++ обработала запрос через свои SCs-продукции.
        """
        if not message or len(message.strip()) < self._MIN_NAME_LENGTH:
            return None

        # Если сообщение похоже на запрос теста — отвечаем напрямую из Python
        if self._matches_any_pattern(message, self._TEST_PATTERNS):
            self.logger.info(
                f"TopicInfoAgent: Handling test directly in Python: {message}"
            )
            test_result = self._handle_test_message(message)
            if test_result:
                return test_result
            self.logger.warning(f"TopicInfoAgent: Could not parse test day from: {message}")

        # Если сообщение похоже на запрос дня учебного плана —
        # пропускаем, чтобы Nika C++ обработала через SCs-продукции
        if self._matches_any_pattern(message, self._DAY_PATTERNS):
            self.logger.info(
                f"TopicInfoAgent: Message matches day pattern, skipping for Nika: {message}"
            )
            return None

        # Если сообщение — ответы на тест (5 цифр от 1 до 4) — проверяем
        if self._ANSWER_PATTERN.match(message.strip()):
            self.logger.info(f"TopicInfoAgent: Handling test answer: {message}")
            answer_result = self._handle_test_answers(message, message_history)
            if answer_result:
                return answer_result
            self.logger.warning(f"TopicInfoAgent: Could not handle test answer: {message}")

        # Определяем контекст дисциплины из истории
        context_discipline_addr = ScAddr()
        if message_history:
            context_discipline_addr = self._detect_context_discipline(message_history)

        # 1. Пробуем как тему в рамках контекстной дисциплины
        if context_discipline_addr.is_valid():
            topic_addr = self._find_topic_with_context(message, context_discipline_addr)
            if topic_addr and topic_addr.is_valid():
                topic_name = self._get_main_idtf(topic_addr) or message
                return self._handle_topic_information(topic_name, message_history)

        # 2. Пробуем глобальный поиск темы
        topic_addr = self._find_entity_by_name("concept_discipline_topic", message)
        if topic_addr and topic_addr.is_valid():
            topic_name = self._get_main_idtf(topic_addr) or message
            return self._handle_topic_information(topic_name, message_history)

        # 3. Пробуем как дисциплину
        discipline_addr = self._find_entity_by_name("concept_discipline", message)
        if discipline_addr and discipline_addr.is_valid():
            discipline_name = self._get_main_idtf(discipline_addr) or message
            return self._handle_discipline_information(discipline_name)

        # 4. Пробуем как понятие
        return self._handle_concept_information(message, message_history)

    def _find_relation_link(self, source_addr: ScAddr, relation_idtf: str) -> str:
        """Прямой шаблонный поиск контента по реляционному отношению"""
        try:
            template = ScTemplate()
            template.triple(source_addr, sc_type.VAR_COMMON_ARC >> "arc", sc_type.VAR_NODE_LINK >> "link")
            template.triple(ScKeynodes[relation_idtf], sc_type.VAR_POS_ARC, "arc")
            results = search_by_template(template)
            if results:
                link = results[0].get("link")
                if link.is_valid():
                    content = get_link_content_data(link)
                    if content:
                        return str(content)
        except Exception as e:
            self.logger.error(f"TopicInfoAgent: Failed to find {relation_idtf}: {e}")
        return ""

    # ==================== Поиск с контекстом ====================

    def _detect_context_discipline(self, message_history: list[str]) -> ScAddr:
        """
        Ищет в истории диалога упоминание дисциплины и возвращает её адрес.
        """
        # Предзагружаем все дисциплины один раз
        discipline_map = {}  # name.lower() -> addr
        template = ScTemplate()
        template.triple(ScKeynodes["concept_discipline"], sc_type.VAR_POS_ARC, sc_type.VAR_NODE >> "discipline")
        results = search_by_template(template)
        for r in results:
            addr = r.get("discipline")
            name = self._get_main_idtf(addr)
            if name:
                discipline_map[name.lower()] = addr

        if not discipline_map:
            return ScAddr()

        # Проверяем последние сообщения (с конца — они свежие)
        for msg in reversed(message_history[-5:]):
            msg_lower = msg.lower()
            for disc_name, disc_addr in discipline_map.items():
                if disc_name in msg_lower:
                    self.logger.info(f"TopicInfoAgent: Detected context discipline: {disc_name}")
                    return disc_addr
        return ScAddr()

    def _find_topic_with_context(self, topic_name: str, context_discipline_addr: ScAddr) -> ScAddr:
        """
        Ищет тему сначала в рамках контекстной дисциплины, потом глобально.
        """
        name_lower = topic_name.lower().strip()

        # 1. Если есть контекст дисциплины — ищем тему в её декомпозиции
        if context_discipline_addr.is_valid():
            topic_addrs = self._get_decomposition_addrs(context_discipline_addr)
            for addr in topic_addrs:
                t_name = self._get_main_idtf(addr)
                if t_name:
                    t_lower = t_name.lower()
                    # Точное совпадение или вхождение
                    if t_lower == name_lower or name_lower in t_lower:
                        return addr
            # Не нашли в контексте дисциплины — пробуем глобальный поиск

        # 2. Глобальный поиск
        return self._find_entity_by_name("concept_discipline_topic", topic_name)

    @staticmethod
    def _names_fuzzy_match(name1: str, name2: str) -> bool:
        """Проверяет, совпадают ли два имени с учётом грамматических падежей.
        Использует проверку общего префикса (≥80% короткого имени)."""
        min_len = min(len(name1), len(name2))
        if min_len < 4:
            return False
        common_prefix = 0
        for i in range(min_len):
            if name1[i] == name2[i]:
                common_prefix += 1
            else:
                break
        return common_prefix >= min_len * 0.8

    def _find_entity_by_name(self, class_idtf: str, name: str) -> ScAddr:
        """
        Ищет сущность заданного класса по названию с улучшенным сопоставлением:
        1. Сначала точное совпадение (без учёта регистра)
        2. Потом частичное совпадение (подстрока)
        3. Потом нечёткое совпадение (общий префикс ≥80%)
        4. Возвращает ScAddr() при неоднозначном результате
        """
        name_clean = name.strip().lower()
        if len(name_clean) < self._MIN_NAME_LENGTH:
            return ScAddr()

        template = ScTemplate()
        template.triple(ScKeynodes[class_idtf], sc_type.VAR_POS_ARC, sc_type.VAR_NODE >> "entity")
        results = search_by_template(template)

        exact_matches = []
        partial_matches = []
        fuzzy_matches = []

        for result in results:
            entity_addr = result.get("entity")
            entity_name = self._get_main_idtf(entity_addr)
            if not entity_name:
                continue

            entity_lower = entity_name.lower()

            # Точное совпадение
            if entity_lower == name_clean:
                exact_matches.append(entity_addr)
            # Подстрока (только если имя достаточно длинное)
            elif len(name_clean) >= self._MIN_NAME_LENGTH and name_clean in entity_lower:
                partial_matches.append(entity_addr)
            # Обратная подстрока: имя сущности содержится во введённом имени
            elif len(entity_lower) >= self._MIN_NAME_LENGTH and entity_lower in name_clean:
                partial_matches.append(entity_addr)
            # Нечёткое совпадение: общий префикс ≥80%
            elif self._names_fuzzy_match(name_clean, entity_lower):
                fuzzy_matches.append(entity_addr)

        # Сначала точное совпадение
        if len(exact_matches) == 1:
            return exact_matches[0]
        if len(exact_matches) > 1:
            return exact_matches[0]
        # Одно частичное совпадение
        if len(partial_matches) == 1:
            return partial_matches[0]
        # Одно нечёткое совпадение
        if len(fuzzy_matches) == 1:
            return fuzzy_matches[0]
        # Нет совпадений или несколько — неоднозначно
        return ScAddr()

    def _get_decomposition_addrs(self, entity_addr: ScAddr) -> list[ScAddr]:
        """Возвращает список адресов элементов декомпозиции"""
        try:
            decomp_set = search_element_by_non_role_relation(
                entity_addr, ScKeynodes["nrel_decomposition"]
            )
            if not decomp_set.is_valid():
                return []
            template = ScTemplate()
            template.triple(decomp_set, sc_type.VAR_POS_ARC, sc_type.VAR_NODE >> "element")
            results = search_by_template(template)
            return [r.get("element") for r in results]
        except Exception:
            return []

    def _find_concept_by_name(self, name: str) -> ScAddr:
        """Ищет понятие по русскому названию с улучшенным сопоставлением."""
        name_clean = name.strip().lower()
        if len(name_clean) < self._MIN_NAME_LENGTH:
            return ScAddr()

        template = ScTemplate()
        template.triple(sc_type.VAR_NODE >> "concept", sc_type.VAR_COMMON_ARC >> "arc", sc_type.VAR_NODE_LINK >> "link")
        template.triple(ScKeynodes["nrel_main_idtf"], sc_type.VAR_POS_ARC, "arc")
        results = search_by_template(template)

        exact = []
        partial = []
        fuzzy = []
        for result in results:
            link_addr = result.get("link")
            if not link_addr.is_valid():
                continue
            try:
                content = get_link_content_data(link_addr)
                if content:
                    text = str(content).lower()
                    if text == name_clean:
                        exact.append(result.get("concept"))
                    elif name_clean in text:
                        # Запрос — подстрока имени понятия (напр. "sc-код" в "алфавит ядра sc-кода")
                        # Предпочитаем более длинные совпадения
                        partial.append((len(text), result.get("concept")))
                    elif text in name_clean:
                        # Имя понятия — подстрока запроса (напр. "sc-код" в "алфавит ядра sc-кода")
                        partial.append((len(text), result.get("concept")))
                    elif self._names_fuzzy_match(name_clean, text):
                        fuzzy.append(result.get("concept"))
            except Exception:
                continue

        if exact:
            return exact[0]
        if partial:
            # Сортируем по длине совпадения: чем длиннее, тем точнее
            partial.sort(key=lambda x: x[0], reverse=True)
            return partial[0][1]
        if fuzzy:
            return fuzzy[0]
        return ScAddr()

    # ==================== Вспомогательные методы ====================

    def _find_all_topic_names(self) -> list[str]:
        """Все названия тем"""
        template = ScTemplate()
        template.triple(ScKeynodes["concept_discipline_topic"], sc_type.VAR_POS_ARC, sc_type.VAR_NODE >> "topic")
        results = search_by_template(template)
        topics = []
        for r in results:
            name = self._get_main_idtf(r.get("topic"))
            if name:
                topics.append(name)
        return topics

    def _get_main_idtf(self, entity_addr: ScAddr) -> str | None:
        """Основной идентификатор сущности"""
        link = search_element_by_non_role_relation(entity_addr, ScKeynodes["nrel_main_idtf"])
        if link.is_valid():
            return str(get_link_content_data(link))
        return None

    def _get_key_concepts_names(self, topic_addr: ScAddr) -> list[str]:
        """Ключевые понятия темы"""
        try:
            key_set = search_element_by_non_role_relation(topic_addr, ScKeynodes["nrel_key_concepts"])
            if not key_set.is_valid():
                return []
            template = ScTemplate()
            template.triple(key_set, sc_type.VAR_POS_ARC, sc_type.VAR_NODE >> "concept")
            results = search_by_template(template)
            names = []
            for r in results:
                name = self._get_main_idtf(r.get("concept"))
                if name:
                    names.append(name)
            return names
        except Exception:
            return []

    def _get_decomposition_names(self, entity_addr: ScAddr) -> list[str]:
        """Названия элементов декомпозиции"""
        try:
            decomp_set = search_element_by_non_role_relation(
                entity_addr, ScKeynodes["nrel_decomposition"]
            )
            if not decomp_set.is_valid():
                return []
            template = ScTemplate()
            template.triple(decomp_set, sc_type.VAR_POS_ARC, sc_type.VAR_NODE >> "element")
            results = search_by_template(template)
            names = []
            for r in results:
                name = self._get_main_idtf(r.get("element"))
                if name:
                    names.append(name)
            return names
        except Exception:
            return []

    # ==================== Отправка ответа ====================

    def _send_reply(self, message_link_addr: ScAddr, reply_text: str) -> ScAddr | None:
        reply_link = generate_link(reply_text)
        generate_non_role_relation(reply_link, message_link_addr, ScKeynodes["nrel_reply_to_message"])
        generate_non_role_relation(reply_link, ScKeynodes["myself"], ScKeynodes["nrel_message_author"])
        return reply_link

    # ==================== История диалога ====================

    def _get_user_dialogue_messages(self, arc_to_message_addr: ScAddr) -> list[str]:
        """Получает историю сообщений в диалоге (от новых к старым)"""
        dialogue_addr = self._get_message_dialogue(arc_to_message_addr)
        if not dialogue_addr.is_valid():
            return []
        messages = []
        try:
            dialogue_set = ScOrientedSet(set_node=dialogue_addr)
            for msg_link in dialogue_set:
                if self._is_message_from_myself(msg_link):
                    continue
                content = get_link_content_data(msg_link)
                if content:
                    messages.append(str(content))
        except Exception as e:
            self.logger.warning(f"TopicInfoAgent: Failed to get dialogue history: {e}")
        # Возвращаем от новых к старым — последнее сообщение (самое свежее) первым
        messages.reverse()
        return messages

    def _get_message_dialogue(self, arc_to_message_addr: ScAddr) -> ScAddr:
        """Получает диалог по дуге к сообщению"""
        templ = ScTemplate()
        templ.triple(sc_type.VAR_NODE >> "dialogue", arc_to_message_addr, sc_type.VAR_NODE)
        results = search_by_template(templ)
        if results:
            return results[0].get("dialogue")
        return ScAddr()

    def _get_message_link(self, arc_to_message_addr: ScAddr) -> ScAddr:
        """Получает файл с сообщением по дуге"""
        templ = ScTemplate()
        templ.quintuple(
            sc_type.VAR_NODE, sc_type.VAR_POS_ARC, sc_type.VAR_NODE_LINK >> "message_link",
            arc_to_message_addr, ScKeynodes["rrel_last"],
        )
        results = search_by_template(templ)
        if results:
            return results[0].get("message_link")
        return ScAddr()

    def _get_message_author_class(self, message_link_addr: ScAddr) -> ScAddr:
        """Класс автора сообщения"""
        author_addr = self._get_message_author(message_link_addr)
        if not author_addr.is_valid():
            return ScAddr()
        templ = ScTemplate()
        templ.triple(sc_type.VAR_NODE_CLASS >> "cls", sc_type.VAR_POS_ARC, author_addr)
        templ.triple(ScKeynodes["concept_user_class"], sc_type.VAR_POS_ARC, "cls")
        results = search_by_template(templ)
        if results:
            return results[0].get("cls")
        return ScAddr()

    def _get_message_author(self, message_link_addr: ScAddr) -> ScAddr:
        """Автор сообщения"""
        templ = ScTemplate()
        templ.quintuple(
            message_link_addr, sc_type.VAR_COMMON_ARC, sc_type.VAR_NODE >> "author",
            sc_type.VAR_POS_ARC, ScKeynodes["nrel_message_author"],
        )
        results = search_by_template(templ)
        if results:
            return results[0].get("author")
        return ScAddr()

    def _is_message_from_myself(self, message_link_addr: ScAddr) -> bool:
        """Проверяет, что сообщение от самого агента"""
        author_addr = self._get_message_author(message_link_addr)
        return author_addr == ScKeynodes["myself"]
