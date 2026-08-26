from __future__ import annotations

from models.entity import Entity
from models.event import Event
from models.relation import Relation
from models.world_state import WorldState
from services.context_builder import ContextBuilder


def build_world() -> WorldState:
    fungoso = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        notes="Le gusta el oro.",
        active=True,
    )

    goblin = Entity(
        id=2,
        name="Goblin",
        entity_type="creature",
        description="Una criatura hostil.",
        notes="Vive cerca de Vorder's Hold.",
        active=True,
    )

    unrelated = Entity(
        id=3,
        name="Aldric",
        entity_type="npc",
        description="Un minero viejo.",
        notes="",
        active=True,
    )

    relation = Relation(
        id="fungoso-goblin",
        subject_id=1,
        relation_type="enemy_of",
        target_id=2,
        metadata={
            "reason": "Intentó robarle",
        },
        active=True,
    )

    event = Event(
        id="event-001",
        event_type="discovery",
        title="La mina abandonada",
        description="Fungoso descubre una mina abandonada.",
        consequences="Se abre una nueva zona de exploración.",
        session_id=1,
        secret=False,
        metadata={
            "entity_ids": [1],
            "location": "Vorder's Hold",
        },
    )

    secret_event = Event(
        id="secret-001",
        event_type="secret",
        title="El verdadero origen del rey",
        description="El rey es realmente un impostor.",
        consequences="El jugador todavía no lo sabe.",
        session_id=1,
        secret=True,
        metadata={
            "entity_ids": [1],
        },
    )

    return WorldState(
        entities={
            1: fungoso,
            2: goblin,
            3: unrelated,
        },
        relations={
            relation.id: relation,
        },
        events={
            event.id: event,
            secret_event.id: secret_event,
        },
    )


def test_context_builder_finds_primary_entity():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert result["query"] == "Fungoso"

    assert len(result["entities"]) == 2

    names = {
        entity["name"]
        for entity in result["entities"]
    }

    assert "Fungoso" in names
    assert "Goblin" in names


def test_context_builder_includes_related_relation():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert len(result["relations"]) == 1

    relation = result["relations"][0]

    assert relation["id"] == "fungoso-goblin"
    assert relation["relation_type"] == "enemy_of"


def test_context_builder_includes_related_public_event():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert len(result["events"]) == 1

    event = result["events"][0]

    assert event["id"] == "event-001"
    assert event["title"] == "La mina abandonada"


def test_context_builder_does_not_include_unrelated_entity():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    names = {
        entity["name"]
        for entity in result["entities"]
    }

    assert "Aldric" not in names


def test_context_builder_does_not_expose_secret_events():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    event_ids = {
        event["id"]
        for event in result["events"]
    }

    assert "secret-001" not in event_ids


def test_context_builder_returns_text_context():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert "context" in result

    context = result["context"]

    assert "Fungoso" in context
    assert "Goblin" in context
    assert "enemy_of" in context
    assert "La mina abandonada" in context


def test_context_builder_empty_query_returns_empty_context():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "   ",
    )

    assert result == {
        "query": "",
        "entities": [],
        "items": [],
        "item_instances": [],
        "resources": [],
        "resource_balances": [],
        "relations": [],
        "events": [],
        "context": "Sin información relevante.",
    }