#!/usr/bin/env python3
"""Тестовый скрипт для проверки концептов — использует sc_client + sc_kpm."""
import sys
import os

# Add the project root to path so imports from problem-solver/py work
sys.path.insert(0, "/home/glehzwmd/OSTIS-Telegram-Assistant/problem-solver/py")

from sc_client import client
from sc_client.models import ScTemplate, ScAddr
from sc_client.constants import sc_type
from sc_client.client import search_by_template
from sc_kpm import ScKeynodes
from sc_kpm.utils import get_link_content_data

CONCEPTS = [
    "concept_knowledge_base",
    "concept_intelligent_system",
    "concept_knowledge_representation",
    "concept_problem_solver",
    "concept_production_knowledge_representation_model",
    "concept_frame_knowledge_representation_model",
    "concept_logic_knowledge_representation_models",
    "concept_semantic_network_knowledge_representation_model",
    "concept_user_interface",
    "concept_problem_solving_model",
]


def check_relation(concept_addr: ScAddr, rel_name: str, rel_label: str) -> bool:
    """Проверяет наличие rel_name у concept_addr."""
    rel_addr = ScKeynodes[rel_name]
    if not rel_addr.is_valid():
        print(f"  ⚠️  Keynode '{rel_name}' not resolved")
        return False

    templ = ScTemplate()
    arc = "_arc"
    link = "_link"
    rel_arc = "_rel_arc"
    templ.triple(concept_addr, sc_type.VAR_COMMON_ARC >> arc, sc_type.VAR_NODE_LINK >> link)
    templ.triple(rel_addr, sc_type.VAR_POS_ARC >> rel_arc, arc)

    results = search_by_template(templ)
    if results:
        link_content = get_link_content_data(results[0].get(link))
        text = str(link_content)[:100] if link_content else "(empty)"
        print(f"  ✅ {rel_label}: {text}")
        return True
    else:
        print(f"  ❌ {rel_label}: MISSING")
        return False


def main():
    print("=" * 60)
    print("ТЕСТ: проверка определений и пояснений концептов")
    print("=" * 60)

    try:
        client.connect("ws://localhost:8090")
        print("✅ Connected to sc-server\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    results = {}
    for concept_idtf in CONCEPTS:
        print(f"--- {concept_idtf} ---")
        concept_addr = ScKeynodes[concept_idtf]
        if not concept_addr.is_valid():
            print(f"  ❌ Concept not found in KB!\n")
            results[concept_idtf] = (False, False)
            continue

        print(f"  Addr: {concept_addr.value}")
        has_def = check_relation(concept_addr, "nrel_definition", "Definition")
        has_expl = check_relation(concept_addr, "nrel_explanation", "Explanation")
        results[concept_idtf] = (has_def, has_expl)
        print()

    client.disconnect()

    print("=" * 60)
    print("РЕЗУЛЬТАТЫ:")
    ok_def = sum(1 for d, _ in results.values() if d)
    ok_expl = sum(1 for _, e in results.values() if e)
    total = len(CONCEPTS)
    missing_def = [k for k, (d, _) in results.items() if not d]
    missing_expl = [k for k, (_, e) in results.items() if not e]

    print(f"  Definitions:   {ok_def}/{total}")
    print(f"  Explanations:  {ok_expl}/{total}")
    if missing_def:
        print(f"  ❌ Missing definitions: {', '.join(missing_def)}")
    if missing_expl:
        print(f"  ❌ Missing explanations: {', '.join(missing_expl)}")
    if ok_def == total and ok_expl == total:
        print("✅ ALL CONCEPTS HAVE BOTH DEFINITION AND EXPLANATION!")
    print("=" * 60)


if __name__ == "__main__":
    main()
