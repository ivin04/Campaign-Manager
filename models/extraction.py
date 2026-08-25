from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractedFact:
    """
    Hecho candidato extraído de USER + ASSISTANT.

    Todavía NO modifica la memoria.
    Solo describe algo que parece haber ocurrido.
    """

    fact_type: str

    data: dict[str, Any] = field(default_factory=dict)

    source: str = ""

    confidence: float = 1.0

    qualifiers: dict[str, Any] = field(default_factory=dict)

FACT_ITEM_FOUND = "ITEM_FOUND"
FACT_ITEM_OBTAINED = "ITEM_OBTAINED"
FACT_ITEM_TRANSFERRED = "ITEM_TRANSFERRED"
FACT_ITEM_LOST = "ITEM_LOST"
FACT_ITEM_DESTROYED = "ITEM_DESTROYED"
FACT_ITEM_CREATED = "ITEM_CREATED"

FACT_RESOURCE_GAINED = "RESOURCE_GAINED"
FACT_RESOURCE_SPENT = "RESOURCE_SPENT"
FACT_RESOURCE_TRANSFERRED = "RESOURCE_TRANSFERRED"

FACT_ENTITY_DISCOVERED = "ENTITY_DISCOVERED"

FACT_RELATION_CREATED = "RELATION_CREATED"
FACT_RELATION_CHANGED = "RELATION_CHANGED"
FACT_RELATION_REMOVED = "RELATION_REMOVED"

FACT_LOCATION_DISCOVERED = "LOCATION_DISCOVERED"

FACT_EVENT = "EVENT"

VALID_FACT_TYPES = {
    FACT_ITEM_FOUND,
    FACT_ITEM_OBTAINED,
    FACT_ITEM_TRANSFERRED,
    FACT_ITEM_LOST,
    FACT_ITEM_DESTROYED,
    FACT_ITEM_CREATED,

    FACT_RESOURCE_GAINED,
    FACT_RESOURCE_SPENT,
    FACT_RESOURCE_TRANSFERRED,

    FACT_ENTITY_DISCOVERED,

    FACT_RELATION_CREATED,
    FACT_RELATION_CHANGED,
    FACT_RELATION_REMOVED,

    FACT_LOCATION_DISCOVERED,

    FACT_EVENT,
}

def validate_fact(fact: ExtractedFact) -> bool:
    """
    Comprueba que el extractor ha producido un hecho válido.
    """

    if not fact.fact_type:
        return False

    if fact.fact_type not in VALID_FACT_TYPES:
        return False

    if not isinstance(fact.data, dict):
        return False

    if not 0 <= fact.confidence <= 1:
        return False

    return True

def validate_facts(
    facts: list[ExtractedFact],
) -> list[ExtractedFact]:

    return [
        fact
        for fact in facts
        if validate_fact(fact)
    ]