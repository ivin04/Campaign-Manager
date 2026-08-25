from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app import app
from models.entity import Entity
from models.event import Event
from models.item import Item
from models.relation import Relation
from models.resource import Resource
from models.world_state import WorldState


client = TestClient(app)


@pytest.fixture
def clean_world():
    """
    Sustituye temporalmente el WorldState utilizado por app.py
    por uno controlado por el test.
    """

    import app as app_module

    original_world = app_module.world_service.world

    world = WorldState()

    app_module.world_service.world = world

    try:
        yield world
    finally:
        app_module.world_service.world = original_world


# ============================================================
# ENTITY
# ============================================================


def test_memory_search_http_finds_entity(clean_world):
    clean_world.entities[1] = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        notes="Le gusta el oro.",
        active=True,
    )

    response = client.get(
        "/memory/search",
        params={"q": "Fungoso"},
    )

    assert response.status_code == 200

    data = response.json()

    assert "entities" in data
    assert len(data["entities"]) == 1

    assert data["entities"][0]["id"] == 1
    assert data["entities"][0]["name"] == "Fungoso"


def test_memory_search_http_is_case_insensitive(clean_world):
    clean_world.entities[1] = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        notes="",
        active=True,
    )

    response = client.get(
        "/memory/search",
        params={"q": "FUNGOSO"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["entities"]) == 1
    assert data["entities"][0]["name"] == "Fungoso"


# ============================================================
# ITEM
# ============================================================


def test_memory_search_http_finds_item(clean_world):
    clean_world.items[1] = Item(
        id=1,
        name="Espada de hierro",
        description="Una espada sencilla.",
        significance="Común",
        unique=False,
        notes="Tiene una pequeña muesca.",
    )

    response = client.get(
        "/memory/search",
        params={"q": "espada"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == 1
    assert data["items"][0]["name"] == "Espada de hierro"


# ============================================================
# RELATION
# ============================================================


def test_memory_search_http_finds_relation(clean_world):
    clean_world.relations["fungoso-goblin"] = Relation(
        id="fungoso-goblin",
        subject_id=1,
        relation_type="enemy_of",
        target_id=2,
        metadata={
            "reason": "Intentó robarle",
        },
        active=True,
    )

    response = client.get(
        "/memory/search",
        params={"q": "enemy_of"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["relations"]) == 1

    relation = data["relations"][0]

    assert relation["id"] == "fungoso-goblin"
    assert relation["subject_id"] == 1
    assert relation["target_id"] == 2


# ============================================================
# PUBLIC EVENT
# ============================================================


def test_memory_search_http_returns_public_event(clean_world):
    clean_world.events["event-001"] = Event(
        id="event-001",
        event_type="discovery",
        title="La mina abandonada",
        description="Fungoso descubre una mina abandonada.",
        consequences="Se abre una nueva zona.",
        session_id=1,
        secret=False,
        metadata={
            "location": "Vorder's Hold",
        },
    )

    response = client.get(
        "/memory/search",
        params={"q": "mina abandonada"},
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data["events"]) == 1

    event = data["events"][0]

    assert event["id"] == "event-001"
    assert event["secret"] is False


# ============================================================
# SECRET EVENT
# ============================================================


def test_memory_search_http_does_not_expose_secret_event(clean_world):
    clean_world.events["secret-001"] = Event(
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

    response = client.get(
        "/memory/search",
        params={"q": "impostor"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["events"] == []


# ============================================================
# CONTEXT
# ============================================================


def test_memory_context_http_returns_context(clean_world):
    clean_world.entities[1] = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        notes="",
        active=True,
    )

    response = client.get(
        "/memory/context",
        params={"q": "Fungoso"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data["query"] == "Fungoso"

    assert "results" in data
    assert "entities" in data["results"]

    assert len(data["results"]["entities"]) == 1
    assert data["results"]["entities"][0]["name"] == "Fungoso"


# ============================================================
# NO RESULTS
# ============================================================


def test_memory_search_http_returns_empty_categories(clean_world):
    response = client.get(
        "/memory/search",
        params={"q": "esto-no-existe"},
    )

    assert response.status_code == 200

    data = response.json()

    assert data == {
        "entities": [],
        "items": [],
        "item_instances": [],
        "resources": [],
        "resource_balances": [],
        "relations": [],
        "events": [],
    }


# ============================================================
# QUERY REQUIRED
# ============================================================


def test_memory_search_http_requires_query():
    response = client.get("/memory/search")

    assert response.status_code == 422


def test_memory_context_http_requires_query():
    response = client.get("/memory/context")

    assert response.status_code == 422