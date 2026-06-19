from sc_client.client import (connect, disconnect, is_connected,
                              search_by_template, generate_by_template,
                              generate_elements, generate_elements_by_scs, search_links_by_contents
                            )
from sc_kpm import ScKeynodes
from sc_client.models import ScAddr, ScTemplate, ScConstruction, ScLinkContentType, ScLinkContent
from sc_client.constants import sc_type
from logger import log
MACHINE_URL = "ws://localhost:8090"


def get_user_class(tg_id: str, user_name: str) -> str:
    """
    Проверяет, известен ли пользователь в БZ.
    Возвращает 'concept_student' | 'concept_known_user' | 'concept_unknown_user'

    Args:
        tg_id: Telegram user ID (как строка)
        user_name: Имя пользователя (для логирования)

    Returns:
        'concept_student' | 'concept_known_user' | 'concept_unknown_user'
    """
    if not is_connected():
        connect(MACHINE_URL)

    try:
        user_addr = _search_user_by_tg_id(tg_id)

        if user_addr.is_valid():
            if _is_student(user_addr):
                log(f"User {tg_id} ({user_name}) found as STUDENT", system="SC_HANDLER")
                return "concept_student"
            else:
                log(f"User {tg_id} ({user_name}) found as KNOWN_USER", system="SC_HANDLER")
                return "concept_user"
        else:
            log(f"User {tg_id} ({user_name}) NOT FOUND in KB - treating as UNKNOWN", system="SC_HANDLER")
            return "concept_unknown_user"

    except Exception as e:
        log(f"Error checking user: {e}", level="error", system="SC_HANDLER")
        return "concept_unknown_user"

def _search_user_by_tg_id(tg_id: str) -> ScAddr:
    """Ищет пользователя в KB по tg_id, возвращает ScAddr узла пользователя."""
    log(f"Searching for user with tg_id: {tg_id}", system="SC_HANDLER")

    found_links = search_links_by_contents(tg_id)[0]

    if not found_links or not found_links[0]:
        log(f"No link found for tg_id {tg_id}", system="SC_HANDLER|SEARCH TG ID")
        return ScAddr()
    log(f"tg_id {tg_id} was found at ScAddr: {found_links[0]}", "info", "SC_HANDLER|SEARCH TG ID")
    tg_id_link = found_links[0]

    nrel_tg_id = ScKeynodes["nrel_user_id"]  # твой идентификатор отношения
    log(f"nrel_user_id ScAddr {nrel_tg_id}", "info", "SC_HANDLER|SEARCH TG ID")
    template = ScTemplate()
    template.quintuple(
        sc_type.VAR_NODE,   # искомый узел пользователя
        sc_type.VAR_COMMON_ARC,        # =>
        tg_id_link,                    # конкретная ссылка с tg_id
        sc_type.VAR_PERM_POS_ARC,      # ->
        nrel_tg_id                     # nrel_tg_id
    )

    results = search_by_template(template)[0]

    if not results:
        log(f"No user node found for tg_id {tg_id}", system="SC_HANDLER|SEARCH TG ID")
        return ScAddr(0)

    user_addr = results.get(0)
    log(f"Found user: {user_addr}", system="SC_HANDLER|SEARCH TG ID")
    return user_addr

def _is_student(user_addr: ScAddr) -> bool:
    try:
        student_class = ScKeynodes["concept_student"]
        templ = ScTemplate()
        templ.triple(
            student_class,
            sc_type.VAR_POS_ARC,
            user_addr
        )
        results = search_by_template(templ)
        return len(results) > 0

    except Exception as e:
        log(f"Error checking if student: {e}", level="error", system="SC_HANDLER|CHECK STUDENT")
        return False

def send_message_to_sc(message: str, tg_id: str, user_name: str) -> None:
    """
    Отправляет сообщение от пользователя в SC-память.

    Args:
        message: Текст сообщения от пользователя
        tg_id: Telegram user ID
        user_name: Имя пользователя

    На текущий момент только определяет класс пользователя.
    """
    if not is_connected():
        connect(MACHINE_URL)
    construct = ScConstruction()

    user_class = get_user_class(tg_id, user_name)
    log(f"Found user class: {user_class}", system="SC_HANDLER|SEND MESSAGE")
    if user_class == "concept_unknown_user":
        log(f"Registering new user with tg_id {tg_id} and name {user_name}", system="SC_HANDLER|SEND MESSAGE")
        user_node_addr = sign_up_new_user(tg_id, user_name)
    else:
        user_node_addr = _search_user_by_tg_id(tg_id)
        log(f"Existing user node found: {user_node_addr}", system="SC_HANDLER|SEND MESSAGE")

    message_link = ScLinkContent(message, ScLinkContentType.STRING)
    construct.generate_link(sc_type.CONST_NODE_LINK, message_link, "_message")

    message_addr = generate_elements(construct)[0]

    template = ScTemplate()
    template.quintuple(
        message_addr,
        sc_type.VAR_COMMON_ARC,
        user_node_addr,
        sc_type.VAR_PERM_POS_ARC,
        ScKeynodes["nrel_message_author"]
    )
    generate_by_template(template)

def sign_up_new_user(tg_id: str, user_name: str) -> ScAddr:
    """
    Регистрирует нового пользователя в KB, создавая узел и связывая его с tg_id.
    """
    if not is_connected():
        connect(MACHINE_URL)
    try:
        construct = ScConstruction()
        tg_id_link = ScLinkContent(tg_id, ScLinkContentType.STRING)
        construct.generate_link(sc_type.CONST_NODE_LINK, tg_id_link)
        tg_id_link_addr = generate_elements(construct)[0]

        construct = ScConstruction()

        user_name_link = ScLinkContent(user_name, ScLinkContentType.STRING)
        construct.generate_link(sc_type.CONST_NODE_LINK, user_name_link)
        user_name_link_addr = generate_elements(construct)[0]

        construct = ScConstruction()

        construct.generate_node(sc_type.CONST_NODE)
        user_node_addr = generate_elements(construct)[0]

        nrel_tg_id_addr = ScKeynodes["nrel_user_id"]
        log(f"Generated new user node: {user_node_addr}, tg_id link: {tg_id_link_addr}", system="SC_HANDLER|SIGN UP")
        template = ScTemplate()
        template.quintuple(
            user_node_addr,
            sc_type.VAR_COMMON_ARC,
            tg_id_link_addr,
            sc_type.VAR_PERM_POS_ARC,
            nrel_tg_id_addr
        )
        template.triple(
            ScKeynodes["concept_user"],
            sc_type.VAR_POS_ARC,
            user_node_addr,
        )
        template.quintuple(
            user_node_addr,
            sc_type.VAR_COMMON_ARC,
            user_name_link_addr,
            sc_type.VAR_PERM_POS_ARC,
            ScKeynodes["nrel_main_idtf"]
        )
        generate_by_template(template)

        return user_node_addr
    except Exception as e:
        log(f"Error signing up new user: {e}", level="error", system="SC_HANDLER|SIGN UP")
        return ScAddr(0)


    # TODO: Здесь будут созданы ноды в SC-machine
if __name__ == "__main__":
    connect(MACHINE_URL)
    send_message_to_sc("Привет, я тестовое сообщение от пользователя!", "7658655979", "TestUser")