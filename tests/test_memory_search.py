from dataclasses import replace

import pytest

import app

from models.world_state import WorldState
from models.entity import Entity
from models.event import Event


@pytest.fixture
def clean_world():
    """
    Sustituye temporalmente el WorldState utilizado por app.py.

    Al terminar cada test restaura el mundo original.
    """

    original_world = app.world_service.world

    # WorldState vacío.
    app.world_service.world = type(original_world)()

    yield app.world_service.world

    app.world_service.world = original_world


def test_memory_search_finds_entity(clean_world):
    """
    /memory/search debe consultar el WorldState y encontrar entidades.
    """

    fungoso = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        notes="Le gusta el oro.",
        active=True,
    )

    clean_world.entities[fungoso.id] = fungoso

    result = app.search_memory("Fungoso")

    assert "entities" in result

    assert len(result["entities"]) == 1

    entity = result["entities"][0]

    assert entity["id"] == 1
    assert entity["name"] == "Fungoso"
    assert entity["entity_type"] == "character"


def test_memory_search_finds_entity_by_description(clean_world):
    """
    La búsqueda no debe limitarse al nombre.

    También debe encontrar una entidad mediante su descripción.
    """

    goblin = Entity(
        id=2,
        name="Goblin",
        entity_type="creature",
        description="Una criatura hostil que vive cerca de la mina.",
        notes="Evita a los aventureros.",
        active=True,
    )

    clean_world.entities[goblin.id] = goblin

    result = app.search_memory("mina")

    assert len(result["entities"]) == 1

    entity = result["entities"][0]

    assert entity["id"] == 2
    assert entity["name"] == "Goblin"


def test_memory_search_ignores_inactive_entities(clean_world):
    """
    Las entidades inactivas no deben formar parte de la memoria recuperada.
    """

    dead_character = Entity(
        id=3,
        name="Personaje muerto",
        entity_type="character",
        description="Ya no existe como entidad activa.",
        notes="",
        active=False,
    )

    clean_world.entities[dead_character.id] = dead_character

    result = app.search_memory("Personaje muerto")

    assert result["entities"] == []


def test_memory_search_does_not_expose_secret_events(clean_world):
    """
    Los eventos secretos nunca deben salir hacia SillyTavern.
    """

    secret_event = Event(
        id="secret-001",
        event_type="secret",
        title="El verdadero origen del rey",
        description="El rey es realmente un impostor.",
        consequences="El jugador todavía no lo sabe.",
        session_id=1,
        secret=True,
        metadata={
            "importance": "critical",
        },
    )

    public_event = Event(
        id="event-001",
        event_type="discovery",
        title="La espada perdida",
        description="Fungoso encuentra una espada.",
        consequences="Ahora posee la espada.",
        session_id=1,
        secret=False,
        metadata={
            "importance": "medium",
        },
    )

    clean_world.events[secret_event.id] = secret_event
    clean_world.events[public_event.id] = public_event

    result = app.search_memory("rey")

    assert result["events"] == []

    result = app.search_memory("espada")

    assert len(result["events"]) == 1
    assert result["events"][0]["id"] == "event-001"


def test_memory_search_finds_public_event(clean_world):
    """
    Los eventos públicos del WorldState sí deben aparecer.
    """

    event = Event(
        id="event-002",
        event_type="discovery",
        title="La mina abandonada",
        description="Los aventureros descubren una mina abandonada.",
        consequences="Se abre una nueva zona de exploración.",
        session_id=2,
        secret=False,
        metadata={
            "location": "Vorder's Hold",
        },
    )

    clean_world.events[event.id] = event

    result = app.search_memory("mina")

    assert len(result["events"]) == 1

    saved_event = result["events"][0]

    assert saved_event["id"] == "event-002"
    assert saved_event["title"] == "La mina abandonada"


def test_memory_search_empty_query_content_returns_empty_result(clean_world):
    """
    Si la consulta solo contiene stopwords, no debe consultar ni devolver nada.
    """

    result = app.search_memory("el la de un")

    assert result == {
        "entities": [],
        "items": [],
        "item_instances": [],
        "resources": [],
        "resource_balances": [],
        "relations": [],
        "events": [],
    }


def test_memory_context_uses_world_state(clean_world):
    """
    /memory/context debe construir el contexto utilizando
    la información recuperada desde el WorldState.
    """

    fungoso = Entity(
        id=10,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        notes="Le gusta el oro.",
        active=True,
    )

    clean_world.entities[fungoso.id] = fungoso

    result = app.memory_context("Fungoso")

    assert result["query"] == "Fungoso"

    assert len(result["entities"]) == 1

    entity = result["entities"][0]

    assert entity["id"] == 10
    assert entity["name"] == "Fungoso"
    assert entity["entity_type"] == "character"
    assert entity["description"] == "Un aventurero peculiar."
    assert entity["notes"] == "Le gusta el oro."

    assert "context" in result
    assert "Fungoso" in result["context"]