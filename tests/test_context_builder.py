from __future__ import annotations

from models.entity import Entity
from models.event import Event
from models.item import Item, ItemInstance
from models.relation import Relation
from models.resource import Resource, ResourceBalance
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

def build_world_with_related_data() -> WorldState:
    fungoso = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
        description="Un aventurero peculiar.",
        active=True,
    )

    unrelated = Entity(
        id=2,
        name="Aldric",
        entity_type="npc",
        description="Un minero viejo.",
        active=True,
    )

    sword = Item(
        id=10,
        name="Espada de hierro",
        description="Una espada sencilla.",
        significance="Arma fiable.",
        unique=False,
        notes="",
    )

    sword_instance = ItemInstance(
        id=100,
        item_id=10,
        instance_number=1,
        owner_id=1,
        location_id=None,
        condition="Bueno",
        notes="Pertenece a Fungoso.",
        active=True,
    )

    unrelated_instance = ItemInstance(
        id=101,
        item_id=10,
        instance_number=2,
        owner_id=2,
        location_id=None,
        condition="Malo",
        notes="Pertenece a Aldric.",
        active=True,
    )

    gold = Resource(
        id=20,
        name="Oro",
        unit="mo",
        notes="Monedas de oro.",
    )

    gold_balance = ResourceBalance(
        id=200,
        resource_id=20,
        owner_id=1,
        amount=150,
        notes="Ahorros de Fungoso.",
    )

    unrelated_balance = ResourceBalance(
        id=201,
        resource_id=20,
        owner_id=2,
        amount=999,
        notes="Ahorros de Aldric.",
    )

    return WorldState(
        entities={
            1: fungoso,
            2: unrelated,
        },
        items={
            10: sword,
        },
        item_instances={
            100: sword_instance,
            101: unrelated_instance,
        },
        resources={
            20: gold,
        },
        resource_balances={
            200: gold_balance,
            201: unrelated_balance,
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

def test_context_builder_includes_owned_item_instance():
    builder = ContextBuilder()

    result = builder.build(
        build_world_with_related_data(),
        "Fungoso",
    )

    instance_ids = {
        instance["id"]
        for instance in result["item_instances"]
    }

    assert 100 in instance_ids
    assert 101 not in instance_ids

def test_context_builder_resolves_parent_item():
    builder = ContextBuilder()

    result = builder.build(
        build_world_with_related_data(),
        "Fungoso",
    )

    item_ids = {
        item["id"]
        for item in result["items"]
    }

    assert 10 in item_ids

def test_context_builder_includes_owned_resource_balance():
    builder = ContextBuilder()

    result = builder.build(
        build_world_with_related_data(),
        "Fungoso",
    )

    balance_ids = {
        balance["id"]
        for balance in result["resource_balances"]
    }

    assert 200 in balance_ids
    assert 201 not in balance_ids

def test_context_builder_resolves_parent_resource():
    builder = ContextBuilder()

    result = builder.build(
        build_world_with_related_data(),
        "Fungoso",
    )

    resource_ids = {
        resource["id"]
        for resource in result["resources"]
    }

    assert 20 in resource_ids

def test_context_builder_does_not_modify_world():
    world = build_world_with_related_data()

    original_items = dict(world.items)
    original_instances = dict(world.item_instances)
    original_resources = dict(world.resources)
    original_balances = dict(
        world.resource_balances
    )

    builder = ContextBuilder()

    builder.build(
        world,
        "Fungoso",
    )

    assert world.items == original_items
    assert world.item_instances == original_instances
    assert world.resources == original_resources
    assert (
        world.resource_balances
        == original_balances
    )