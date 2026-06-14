class MessageClassifier:
    """
    Класс MessageClassifier предназначен для базовой классификации сообщений от пользователя (например, студента)
    по заранее определённым шаблонам.

    Основная задача — определить класс сообщения, извлечь при необходимости сущности и их классы,
    и вернуть результат в стандартизированной структуре.
    """

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
            # Приветственное сообщение
            if "Привет" in message:
                return ["concept_student_message_about_greeting", {}, {}]

            # Неформальное приветствие
            if "Как дела" in message:
                return ["concept_student_message_about_casual_greeting", {}, {}]

             # Запрос о навыках системы
            if "Что ты умеешь" in message:
                return ["concept_student_message_about_searching_my_skills", {}, {}]

            # Запрос о помощи
            if "Мне нужна помощь" in message:
                return ["concept_student_message_about_help", {}, {}]

            # Запрос определения понятия
            if "Что такое" in message:
                entity = message.split("Что такое")[1].strip()
                entity_class = "concept"
                return ["concept_student_message_about_searching_concept_information", {entity_class: entity}, {}]

        return ["concept_unknown_message", {}, {}]
