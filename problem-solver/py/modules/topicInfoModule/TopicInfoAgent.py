import logging
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


    def _generate_reply(self, message_class: str, entities: dict, message_history: list[str] = None, message: str = None) -> str | None:
        """Генерирует ответ в зависимости от класса сообщения"""
        if message_class == "concept_student_message_about_searching_all_topics":
            return self._handle_all_topics()
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

    def _handle_unknown_as_topic(self, message: str, message_history: list[str] = None) -> str | None:
        """
        Пытается найти тему или понятие по тексту сообщения.
        Используется, когда классификатор не распознал запрос.
        Делегирует существующим обработчикам _handle_topic_information и _handle_concept_information.
        """
        if not message or len(message.strip()) < self._MIN_NAME_LENGTH:
            return None

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
            # Не нашли в контексте — не ищем глобально, чтобы не получить тему из другой дисциплины
            return ScAddr()

        # 2. Глобальный поиск (только если нет контекста)
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
