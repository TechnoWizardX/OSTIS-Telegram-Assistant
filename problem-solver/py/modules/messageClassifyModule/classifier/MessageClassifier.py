class MessageClassifier:
    """
    Класс MessageClassifier предназначен для базовой классификации сообщений от пользователя (например, студента)
    по заранее определённым шаблонам.

    Основная задача — определить класс сообщения, извлечь при необходимости сущности и их классы,
    и вернуть результат в стандартизированной структуре.
    """

    # Распространённые опечатки и орфографические ошибки → правильная форма
    _TYPO_FIXES = {
        "раскажи": "расскажи",
        "роскажи": "расскажи",
        "расскаджи": "расскажи",
        "абъясни": "объясни",
        "обесни": "объясни",
        "обьясни": "объясни",
        "апределение": "определение",
        "опредиление": "определение",
        "определения": "определение",
        "инфармацию": "информацию",
        "информацыю": "информацию",
        "инфармацыю": "информацию",
        "панятие": "понятие",
        "панятия": "понятие",
        "понятия": "понятие",
        "панатия": "понятие",
        "тему": "тема",
        "тиму": "тема",
        "дысциплина": "дисциплина",
        "дисцеплина": "дисциплина",
        "дысцыплина": "дисциплина",
        "перчисли": "перечисли",
        "пиричисли": "перечисли",
        "список": "список",
        "спиcок": "список",
        "памоги": "помоги",
        "памаги": "помоги",
        "делаешь": "умеешь",
        "приветствую": "привет",
        "здарова": "привет",
        "здраствуй": "здравствуй",
        "здраствуйте": "здравствуй",
        "здравствуйте": "здравствуй",
    }

    @staticmethod
    def _normalize_typos(text: str) -> str:
        """Исправляет распространённые опечатки и орфографические ошибки."""
        words = text.split()
        fixed = []
        for w in words:
            # Убираем знаки препинания для поиска в словаре
            clean = w.strip(".,!?;:()\"'")
            if clean in MessageClassifier._TYPO_FIXES:
                fixed.append(MessageClassifier._TYPO_FIXES[clean])
            else:
                fixed.append(w)
        return " ".join(fixed)

    @staticmethod
    def _extract_entity(msg_lower: str, message: str, pattern: str) -> str:
        """Извлекает сущность из сообщения после указанного шаблона и очищает пунктуацию."""
        idx = msg_lower.index(pattern) + len(pattern)
        entity = message[idx:].strip()
        return entity.rstrip(".,!?;:()\"'")

    def classify(self, message: str, message_author_class: str, message_history: list[str]) -> tuple[str, dict[str], set[str]]:
        """
        Классифицирует текстовое сообщение, исходя из его содержания и принадлежности отправителя к определённому классу.

        Параметры
        ----------
        message : str
            Текст сообщения, подлежащий анализу и классификации.
        message_author_class : str
            Класс автора сообщения (например: "concept_student").
        message_history : list[str]
            История предыдущих сообщений пользователя для контекстного анализа.

        Возвращает
        ----------
        tuple[str, dict[str], set[str]]
            Кортеж из трёх элементов:
            1. Системный идентификатор класса сообщения (например: "concept_student_message_about_greeting").
            2. Основные идентификаторы сущностей и системные идентификаторы их классов, извлечённых из сообщения
            (например: {"concept": "интеллект"}).
            3. Системные идентификаторы классов сущностей, извлечённых из контекста сообщения.
        """
        if message_author_class == "concept_student":
            msg_lower = MessageClassifier._normalize_typos(message.lower())

            if any(phrase in msg_lower for phrase in ["привет", "здравствуй", "добрый день", "доброе утро", "добрый вечер"]):
                return ["concept_student_message_about_greeting", {}, {}]
            if any(phrase in msg_lower for phrase in ["как дела", "как ты", "что нового"]):
                return ["concept_student_message_about_casual_greeting", {}, {}]

            if any(phrase in msg_lower for phrase in ["что ты умеешь", "твои навыки", "какие у тебя навыки", "что ты можешь"]):
                return ["concept_student_message_about_searching_my_skills", {}, {}]
            if any(phrase in msg_lower for phrase in ["мне нужна помощь", "помоги мне"]):
                return ["concept_student_message_about_help", {}, {}]

            concept_specific_patterns = [
                ("расскажи про понятие ", "concept"),
                ("расскажи о понятии ", "concept"),
                ("объясни понятие ", "concept"),
                ("что ты знаешь про понятие ", "concept"),
                ("что ты знаешь о понятии ", "concept"),
            ]
            for pattern, entity_class in concept_specific_patterns:
                if pattern in msg_lower:
                    entity = self._extract_entity(msg_lower, message, pattern)
                    if entity:
                        return ["concept_student_message_about_searching_concept_information", {entity_class: entity}, {}]
                    return ["concept_student_message_about_searching_concept_information", {}, {}]

            discipline_detail_patterns = [
                ("расскажи подробнее про ", "concept_discipline"),
                ("расскажи подробнее о ", "concept_discipline"),
                ("подробнее про ", "concept_discipline"),
                ("подробнее о ", "concept_discipline"),
                ("что ты знаешь про дисциплину ", "concept_discipline"),
                ("что ты знаешь о дисциплине ", "concept_discipline"),
                ("что надо делать по дисциплине ", "concept_discipline"),
                ("что можешь рассказать про дисциплину ", "concept_discipline"),
                ("что можешь рассказать о дисциплине ", "concept_discipline"),
                ("пришли информацию по дисциплине ", "concept_discipline"),
                ("пришли инфу по дисциплине ", "concept_discipline"),
                ("информацию по дисциплине ", "concept_discipline"),
                ("расскажи про дисциплину ", "concept_discipline"),
                ("расскажи о дисциплине ", "concept_discipline"),
                ("расскажи про предмет ", "concept_discipline"),
                ("расскажи о предмете ", "concept_discipline"),
            ]
            for pattern, entity_class in discipline_detail_patterns:
                if pattern in msg_lower:
                    entity = self._extract_entity(msg_lower, message, pattern)
                    if entity:
                        return ["concept_student_message_about_searching_discipline_information", {entity_class: entity}, {}]
                    return ["concept_student_message_about_searching_discipline_information", {}, {}]

            topic_detail_patterns = [
                ("расскажи подробнее про тему ", "concept_discipline_topic"),
                ("расскажи подробнее о теме ", "concept_discipline_topic"),
                ("расскажи про тему ", "concept_discipline_topic"),
                ("расскажи о теме ", "concept_discipline_topic"),
                ("что ты знаешь по теме ", "concept_discipline_topic"),
                ("что ты знаешь о теме ", "concept_discipline_topic"),
                ("подробнее по теме ", "concept_discipline_topic"),
                ("подробнее о теме ", "concept_discipline_topic"),
                ("пришли информацию по теме ", "concept_discipline_topic"),
                ("пришли инфу по теме ", "concept_discipline_topic"),
                ("информацию по теме ", "concept_discipline_topic"),
                ("инфу по теме ", "concept_discipline_topic"),
                ("расскажи про ", "concept_discipline_topic"),
            ]
            for pattern, entity_class in topic_detail_patterns:
                if pattern in msg_lower:
                    entity = self._extract_entity(msg_lower, message, pattern)
                    if entity:
                        return ["concept_student_message_about_searching_discipline_topic_information", {entity_class: entity}, {}]
                    return ["concept_student_message_about_searching_discipline_topic_information", {}, {}]

            discipline_topics_patterns = [
                ("какие темы есть по ", "concept_discipline"),
                ("какие темы по дисциплине ", "concept_discipline"),
                ("какие разделы есть по ", "concept_discipline"),
                ("какие разделы по дисциплине ", "concept_discipline"),
                ("перечисли темы по ", "concept_discipline"),
                ("перечисли разделы по ", "concept_discipline"),
                ("пришли перечень тем по дисциплине ", "concept_discipline"),
                ("пришли темы по ", "concept_discipline"),
                ("темы по дисциплине ", "concept_discipline"),
                ("разделы по дисциплине ", "concept_discipline"),
                ("список тем по ", "concept_discipline"),
                ("список разделов по ", "concept_discipline"),
            ]
            for pattern, entity_class in discipline_topics_patterns:
                if pattern in msg_lower:
                    entity = self._extract_entity(msg_lower, message, pattern)
                    if entity:
                        return ["concept_student_message_about_searching_discipline_topics", {entity_class: entity}, {}]
                    return ["concept_student_message_about_searching_discipline_topics", {}, {}]

            if any(phrase in msg_lower for phrase in [
                "какие понятия ты знаешь",
                "какие понятия знаешь",
                "какие есть понятия",
                "какие понятия есть",
                "список понятий",
                "перечень понятий",
                "все понятия",
                "перечисли понятия",
                "скинь все понятия",
                "что ты знаешь про понятия",
                "какие термины ты знаешь",
                "какие термины знаешь",
                "список терминов",
                "перечень терминов",
                "все термины",
                "перечисли термины",
            ]):
                return ["concept_student_message_about_searching_concepts", {}, {}]

            if any(phrase in msg_lower for phrase in [
                "какие темы ты знаешь",
                "какие темы есть",
                "какие у тебя есть темы",
                "какие разделы ты знаешь",
                "какие разделы есть",
                "расскажи про свои темы",
                "расскажи про свои разделы",
                "что ты знаешь по темам",
                "что ты знаешь по разделам",
                "перечень всех тем",
                "перечень всех разделов",
                "список всех тем",
                "список всех разделов",
                "все темы",
                "все разделы",
                "скинь все темы",
                "перечисли темы",
                "перечисли разделы",
            ]):
                return ["concept_student_message_about_searching_all_topics", {}, {}]

            if any(phrase in msg_lower for phrase in [
                "какие дисциплины",
                "какие дисциплины изучаем",
                "какие дисциплины изучаю",
                "какие дисциплины доступны",
                "какие предметы",
                "какие предметы изучаю",
                "какие предметы есть",
                "какие курсы",
                "список дисциплин",
                "список предметов",
                "перечень дисциплин",
                "перечень предметов",
            ]):
                return ["concept_student_message_about_searching_studied_disciplines", {}, {}]

            what_is_patterns = [
                "что такое ",
                "что это ",
                "что значит ",
                "что означает ",
                "кто такой ",
                "кто такие ",
                "какое определение у ",
                "какое определение имеет ",
                "дай определение ",
                "дайте определение ",
                "определение понятия ",
                "что ты знаешь про понятие ",
                "что ты знаешь о понятии ",
                "объясни понятие ",
                "объясни ",
                "расскажи про понятие ",
                "расскажи о понятии ",
                "как понять ",
                "что ты знаешь про ",
                "что ты знаешь о ",
            ]
            for pattern in what_is_patterns:
                if pattern in msg_lower:
                    entity = self._extract_entity(msg_lower, message, pattern)
                    if entity:
                        return ["concept_student_message_about_searching_concept_information", {"concept": entity}, {}]
                    return ["concept_student_message_about_searching_concept_information", {}, {}]

        return ["concept_unknown_message", {}, {}]
