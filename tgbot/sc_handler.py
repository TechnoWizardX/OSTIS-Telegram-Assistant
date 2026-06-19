from sc_client.client import (connect, disconnect, is_connected,
                              search_by_template, generate_by_template,
                              generate_elements, search_links_by_contents, create_elementary_event_subscriptions, get_link_content)
from sc_kpm import ScKeynodes
from sc_client.models import ScAddr, ScTemplate, ScConstruction, ScLinkContentType, ScLinkContent, ScEventSubscriptionParams
from sc_client.constants import sc_type
from sc_client.constants.common import ScEventType
from logger import log
from time import sleep
from pathlib import Path

MACHINE_URL = "ws://localhost:8090"


def get_user_class(tg_id: str, user_name: str) -> str:
    """Проверяет, известен ли пользователь в БЗ."""
    if not is_connected():
        connect(MACHINE_URL)

    try:
        user_addr = _search_user_by_tg_id(tg_id)

        if user_addr.is_valid():
            if _is_student(user_addr):
                log(f"User {tg_id} ({user_name}) found as STUDENT", system="SC_HANDLER")
                return "concept_student"
            else:
                log(f"User {tg_id} ({user_name}) found as USER", system="SC_HANDLER")
                return "concept_user"
        else:
            log(f"User {tg_id} ({user_name}) NOT FOUND in KB - treating as UNKNOWN",
                system="SC_HANDLER")
            return "concept_unknown_user"

    except Exception as e:
        log(f"Error checking user: {e}", level="error", system="SC_HANDLER")
        return "concept_unknown_user"


def _search_user_by_tg_id(tg_id: str) -> ScAddr:
    """Ищет пользователя в KB по tg_id. Перебирает ВСЕ найденные ссылки."""
    log(f"Searching for user with tg_id: {tg_id}", system="SC_HANDLER|SEARCH TG ID")

    links_result = search_links_by_contents(tg_id)
    log(f"search_links_by_contents returned: {links_result}", system="SC_HANDLER|SEARCH TG ID")

    if not links_result:
        log(f"No links found for tg_id {tg_id}", system="SC_HANDLER|SEARCH TG ID")
        return ScAddr()

    for batch in links_result:
        for tg_id_link in batch:
            if not tg_id_link.is_valid():
                continue

            log(f"Trying link {tg_id_link} for tg_id {tg_id}",
                system="SC_HANDLER|SEARCH TG ID")

            template = ScTemplate()
            template.quintuple(
                sc_type.VAR_NODE >> "tg_id_user",
                sc_type.VAR_COMMON_ARC,
                tg_id_link,
                sc_type.VAR_PERM_POS_ARC,
                ScKeynodes["nrel_user_id"]
            )

            results = search_by_template(template)
            log(f"  quintuple search results: {results}", system="SC_HANDLER|SEARCH TG ID")

            if results:
                user_addr = results[0].get("tg_id_user")
                log(f"  Found user: {user_addr} via link {tg_id_link}",
                    system="SC_HANDLER|SEARCH TG ID")
                return user_addr

    log(f"No user node found for any link of tg_id {tg_id}",
        system="SC_HANDLER|SEARCH TG ID")
    return ScAddr()


def _is_student(user_addr: ScAddr) -> bool:
    try:
        student_class = ScKeynodes["concept_student"]
        templ = ScTemplate()
        templ.triple(student_class, sc_type.VAR_PERM_POS_ARC, user_addr)
        results = search_by_template(templ)
        return len(results) > 0
    except Exception as e:
        log(f"Error checking if student: {e}", level="error",
            system="SC_HANDLER|CHECK STUDENT")
        return False


def send_message_to_sc(message: str, tg_id: str, user_name: str) -> None:
    """Отправляет сообщение от пользователя в SC-память."""
    log(f"=== send_message_to_sc: tg_id={tg_id}, user={user_name} ===", system="SC_HANDLER")
    log(f"Message text: {message}", system="SC_HANDLER")

    if not is_connected():
        connect(MACHINE_URL)

    user_class = get_user_class(tg_id, user_name)
    log(f"User class: {user_class}", system="SC_HANDLER|SEND MESSAGE")

    if user_class == "concept_unknown_user":
        log(f"Registering new user: tg_id={tg_id}, name={user_name}",
            system="SC_HANDLER|SEND MESSAGE")
        user_node_addr = sign_up_new_user(tg_id, user_name)
        log(f"New user node: {user_node_addr}", system="SC_HANDLER|SEND MESSAGE")
    else:
        user_node_addr = _search_user_by_tg_id(tg_id)
        log(f"Existing user node: {user_node_addr}", system="SC_HANDLER|SEND MESSAGE")

    if not user_node_addr.is_valid():
        log(f"ERROR: Failed to get user node for {tg_id}", level="error",
            system="SC_HANDLER|SEND MESSAGE")
        return

    # Создаём сообщение
    construct = ScConstruction()
    construct.generate_link(
        sc_type.CONST_NODE_LINK,
        ScLinkContent(message, ScLinkContentType.STRING),
        "_message"
    )
    message_addr = generate_elements(construct)[0]
    log(f"Created message link: {message_addr}", system="SC_HANDLER|SEND MESSAGE")

    # Привязываем автора: message --common_arc--> user, arc приписан к nrel_message_author
    template = ScTemplate()
    template.quintuple(
        message_addr,
        sc_type.VAR_COMMON_ARC,
        user_node_addr,
        sc_type.VAR_PERM_POS_ARC,
        ScKeynodes["nrel_message_author"]
    )
    generate_by_template(template)
    log(f"nrel_message_author relation created", system="SC_HANDLER|SEND MESSAGE")

    log(f"=== DONE: message sent by {tg_id} ===", system="SC_HANDLER")


def sign_up_new_user(tg_id: str, user_name: str) -> ScAddr:
    """Регистрирует нового пользователя в KB."""
    if not is_connected():
        connect(MACHINE_URL)
    try:
        # Создаём ссылку с tg_id
        construct = ScConstruction()
        construct.generate_link(sc_type.CONST_NODE_LINK,
                                ScLinkContent(tg_id, ScLinkContentType.STRING), "_tg_id_link")
        [tg_id_link_addr] = generate_elements(construct)

        # Создаём ссылку с именем
        construct = ScConstruction()
        construct.generate_link(sc_type.CONST_NODE_LINK,
                                ScLinkContent(user_name, ScLinkContentType.STRING), "_user_name_link")
        [user_name_link_addr] = generate_elements(construct)

        # Создаём узел пользователя
        construct = ScConstruction()
        construct.generate_node(sc_type.CONST_NODE, "_user_node")
        [user_node_addr] = generate_elements(construct)

        log(f"Generated: user_node={user_node_addr}, tg_id_link={tg_id_link_addr}",
            system="SC_HANDLER|SIGN UP")

        # Отдельно создаём каждое отношение
        # 1. nrel_user_id: user_node --arc--> tg_id_link
        tmpl = ScTemplate()
        tmpl.quintuple(user_node_addr, sc_type.VAR_COMMON_ARC, tg_id_link_addr,
                       sc_type.VAR_PERM_POS_ARC, ScKeynodes["nrel_user_id"])
        generate_by_template(tmpl)
        log("  Created nrel_user_id relation", system="SC_HANDLER|SIGN UP")

        # 2. concept_user: user_node принадлежит классу
        tmpl = ScTemplate()
        tmpl.triple(ScKeynodes["concept_student"], sc_type.VAR_PERM_POS_ARC, user_node_addr)
        generate_by_template(tmpl)
        log("  Created concept_user membership", system="SC_HANDLER|SIGN UP")

        # 3. nrel_main_idtf: user_node --arc--> имя
        tmpl = ScTemplate()
        tmpl.quintuple(user_node_addr, sc_type.VAR_COMMON_ARC, user_name_link_addr,
                       sc_type.VAR_PERM_POS_ARC, ScKeynodes["nrel_main_idtf"])
        generate_by_template(tmpl)
        log("  Created nrel_main_idtf relation", system="SC_HANDLER|SIGN UP")

        # 4. Пишем .scs файл (для rebuild KB)
        safe_id = f"tg_user_{tg_id}"
        scs = (f"{safe_id}\n"
               f"    => nrel_user_id: [{tg_id}];\n"
               f"    => nrel_main_idtf: [{user_name}];\n"
               f"    <- concept_student;;\n")
        dir_path = Path(__file__).parent.parent / "knowledge-base" / "users" / "tgusers" / f"user_{tg_id}.scs"
        dir_path.parent.mkdir(parents=True, exist_ok=True)
        with dir_path.open('w', encoding='utf-8') as f:
            f.write(scs)
        log(f"  Wrote {dir_path}", system="SC_HANDLER|SIGN UP")

        return user_node_addr
    except Exception as e:
        log(f"Error signing up new user: {e}", level="error",
            system="SC_HANDLER|SIGN UP")
        return ScAddr()

def subscribe_to_message(message_adder = None) -> list:
        nrel_reply_to_message = "nrel_reply_to_message"
        nrel_message_author = "nrel_message_author"

        nrel_reply_to_message = ScKeynodes[nrel_reply_to_message]


        def on_message_replied(subscribed_addr: ScAddr, arc: ScAddr,
                               message_to_reply_message_arc_addr: ScAddr):
            reply_message_alias = "_reply_message"
            message_alias = "_message"
            nrel_message_author = ScKeynodes["nrel_message_author"]

            template = ScTemplate()
            template.triple(
                sc_type.VAR_NODE_LINK >> reply_message_alias,
                message_to_reply_message_arc_addr,
                sc_type.VAR_NODE_LINK >> message_alias
            )
            result = search_by_template(template)
            if not result:
                return
            reply_message_addr = result[0].get(reply_message_alias)
            text = get_link_content(reply_message_addr)[0].data
            message_addr = result[0].get(message_alias)

            template = ScTemplate()
            template.quintuple(
                message_addr,
                sc_type.VAR_COMMON_ARC,
                sc_type.VAR_NODE >> "_user",
                sc_type.VAR_PERM_POS_ARC,
                nrel_message_author
            )
            result = search_by_template(template)
            if not result:
                return
            user_addr = result[0].get("_user")
            print(text, " \n=======================\n", user_addr)
            nrel_user_id = ScKeynodes["nrel_user_id"]
            template = ScTemplate()
            template.quintuple(
                user_addr,
                sc_type.VAR_COMMON_ARC,
                sc_type.VAR_NODE_LINK >> "_user_id",
                sc_type.VAR_PERM_POS_ARC,
                nrel_user_id
            )
            result = search_by_template(template)
            if not result:
                return
            user_id = int(get_link_content(result[0].get("_user_id"))[0].data)
            print(user_id)

        event_params = ScEventSubscriptionParams(nrel_reply_to_message,
                                                    ScEventType.AFTER_GENERATE_OUTGOING_ARC, on_message_replied)
        return create_elementary_event_subscriptions(event_params)


if __name__ == "__main__":
    connect(MACHINE_URL)
    log("Connected to SC-machine. Sending test message...", system="SC_HANDLER")
    subscribe_to_message()
    send_message_to_sc("Что такое", "3327799189", "TestUser")
    sleep(5)
    disconnect()
