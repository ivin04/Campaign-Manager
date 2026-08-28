from __future__ import annotations

import pytest

from models.entity import Entity
from models.event import Event
from models.relation import Relation
from models.world_state import WorldState
from services.context_expander import ContextExpander

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

def test_context_expander_relation_relevance_propagates():
    context_expander = ContextExpander()

    world = WorldState()

    fungoso = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Aventurero.",
        active=True,
    )

    aldric = Entity(
        id=2,
        name="Aldric",
        entity_type="npc",
        description="Aliado.",
        active=True,
    )

    world.entities[1] = fungoso
    world.entities[2] = aldric

    relation = Relation(
        id=1,
        subject_id=1,
        target_id=2,
        relation_type="friend",
        active=True,
    )

    world.relations[1] = relation

    result = context_expander.expand_entities(
        world,
        [
            {
                "id": 1,
                "name": "Fungoso",
            }
        ],
        max_depth=1,
    )

    ids = {
        entity["id"]
        for entity in result
    }

    assert 1 in ids
    assert 2 in ids

def test_context_expander_related_entity_relevance_is_below_direct():
    context_expander = ContextExpander()

    world = build_world()

    result = context_expander.expand_entities(
        world,
        [{"id": 1}],
        max_depth=1,
    )

    relevance = {
        entity["id"]: entity.get("_relevance")
        for entity in result
    }

    assert relevance[1] == 1.0
    assert relevance[2] < relevance[1]

def test_context_expander_strong_relation_beats_weak_relation():
    context_expander = ContextExpander()

    world = WorldState()

    first = Entity(
        id=1,
        name="Heroe",
        entity_type="character",
        description="",
        active=True,
    )

    friend = Entity(
        id=2,
        name="Amigo",
        entity_type="npc",
        description="",
        active=True,
    )

    stranger = Entity(
        id=3,
        name="Conocido",
        entity_type="npc",
        description="",
        active=True,
    )

    world.entities = {
        1: first,
        2: friend,
        3: stranger,
    }

    world.relations = {
        1: Relation(
            id=1,
            subject_id=1,
            relation_type="friend",
            target_id=2,
            active=True,
        ),
        2: Relation(
            id=2,
            subject_id=1,
            relation_type="knows",
            target_id=3,
            active=True,
        ),
    }

    result = context_expander.expand_entities(
        world,
        [{"id": 1}],
        max_depth=1,
    )

    relevance = {
        entity["id"]: entity["_relevance"]
        for entity in result
    }

    assert relevance[1] == 1.0
    assert relevance[2] > relevance[3]