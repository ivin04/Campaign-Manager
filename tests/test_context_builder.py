from __future__ import annotations

import pytest

from models.entity import Entity
from models.event import Event
from models.item import Item, ItemInstance
from models.relation import Relation
from models.resource import Resource, ResourceBalance
from models.world_state import WorldState
from services.context_builder import ContextBuilder
from services.context_ranker import ContextRanker
from services.memory_search_service import MemorySearchService


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

def test_context_builder_orders_direct_entities_before_related():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert result["entities"][0]["name"] == "Fungoso"
    assert result["entities"][1]["name"] == "Goblin"


def test_context_builder_respects_context_budget():
    builder = ContextBuilder(
        max_context_chars=60,
    )

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert len(result["context"]) <= 60


def test_context_builder_rejects_invalid_context_budget():
    try:
        ContextBuilder(
            max_context_chars=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_context_builder_rejects_non_integer_context_budget():
    try:
        ContextBuilder(
            max_context_chars="6000",
        )
    except TypeError:
        pass
    else:
        raise AssertionError(
            "Expected TypeError"
        )


def test_context_builder_does_not_modify_entities():
    world = build_world()

    builder = ContextBuilder()

    before = {
        entity_id: entity.name
        for entity_id, entity
        in world.entities.items()
    }

    builder.build(
        world,
        "Fungoso",
    )

    after = {
        entity_id: entity.name
        for entity_id, entity
        in world.entities.items()
    }

    assert before == after

def test_context_builder_strong_relation_has_higher_relevance():
    builder = ContextBuilder()

    assert (
        builder._get_relation_relevance("friend")
        >
        builder._get_relation_relevance("knows")
    )


def test_context_builder_relation_relevance_is_case_insensitive():
    builder = ContextBuilder()

    assert (
        builder._get_relation_relevance("FRIEND")
        ==
        builder._get_relation_relevance("friend")
    )

# ============================================================
# CONTEXT CANDIDATE SCORING
# ============================================================


def test_context_builder_direct_entity_has_higher_score_than_related():
    builder = ContextBuilder()

    direct = {
        "id": 1,
        "name": "Fungoso",
        "_relevance": 1.0,
    }

    related = {
        "id": 2,
        "name": "Aldric",
        "_relevance": 0.7,
    }

    direct_score = builder._entity_context_score(
        direct,
        "Fungoso",
    )

    related_score = builder._entity_context_score(
        related,
        "Fungoso",
    )

    assert direct_score > related_score


def test_context_builder_non_matching_candidate_gets_no_bonus():
    builder = ContextBuilder()

    data = {
        "name": "Aldric",
        "description": "Un minero viejo.",
    }

    score = builder._direct_match_bonus(
        data,
        "fungoso",
    )

    assert score == 0.0


def test_context_builder_word_matching_contributes_to_score():
    builder = ContextBuilder()

    text = "- Fungoso (character): aventurero peculiar"

    score = builder._score_context_candidate(
        text,
        "fungoso peculiar",
        1.0,
    )

    assert score > 1.0


def test_context_builder_empty_query_keeps_base_score():
    builder = ContextBuilder()

    score = builder._score_context_candidate(
        "- Fungoso",
        "",
        1.0,
    )

    assert score == 1.0


# ============================================================
# CONTEXT CANDIDATES
# ============================================================


def test_context_builder_builds_candidates_for_all_categories():
    builder = ContextBuilder()

    result = builder.build(
        build_world_with_related_data(),
        "Fungoso",
    )

    candidates = builder._build_context_candidates(
        result,
        "fungoso",
    )

    categories = {
        candidate["category"]
        for candidate in candidates
    }

    assert "entities" in categories
    assert "items" in categories
    assert "item_instances" in categories
    assert "resources" in categories
    assert "resource_balances" in categories


def test_context_builder_candidates_have_required_fields():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    candidates = builder._build_context_candidates(
        result,
        "fungoso",
    )

    assert candidates

    for candidate in candidates:
        assert "category" in candidate
        assert "text" in candidate
        assert "score" in candidate
        assert "category_order" in candidate
        assert "index" in candidate


def test_context_builder_candidate_scores_are_numeric():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    candidates = builder._build_context_candidates(
        result,
        "fungoso",
    )

    assert candidates

    for candidate in candidates:
        assert isinstance(
            candidate["score"],
            (int, float),
        )


# ============================================================
# CONTEXT RENDERING
# ============================================================


def test_context_builder_renders_category_headers():
    builder = ContextBuilder()

    candidates = [
        {
            "category": "entities",
            "text": "- Fungoso (character)",
            "score": 1.0,
            "category_order": 0,
            "index": 0,
        },
        {
            "category": "relations",
            "text": "- enemy_of: 1 -> 2",
            "score": 0.8,
            "category_order": 1,
            "index": 0,
        },
        {
            "category": "events",
            "text": "- La mina abandonada",
            "score": 0.7,
            "category_order": 2,
            "index": 0,
        },
    ]

    context = builder._render_selected_candidates(
        candidates
    )

    assert "[ENTIDADES]" in context
    assert "[RELACIONES]" in context
    assert "[EVENTOS]" in context


def test_context_builder_does_not_repeat_category_header():
    builder = ContextBuilder()

    candidates = [
        {
            "category": "entities",
            "text": "- Fungoso (character)",
            "score": 1.0,
            "category_order": 0,
            "index": 0,
        },
        {
            "category": "entities",
            "text": "- Goblin (creature)",
            "score": 0.9,
            "category_order": 0,
            "index": 1,
        },
    ]

    context = builder._render_selected_candidates(
        candidates
    )

    assert context.count("[ENTIDADES]") == 1
    assert "- Fungoso (character)" in context
    assert "- Goblin (creature)" in context


def test_context_builder_empty_candidates_render_empty_context():
    builder = ContextBuilder()

    context = builder._render_selected_candidates(
        []
    )

    assert context == "Sin información relevante."


# ============================================================
# CONTEXT SELECTION
# ============================================================


def test_context_builder_prefers_higher_scored_candidates():
    builder = ContextBuilder(
        max_context_chars=100,
    )

    result = {
        "query": "Fungoso",
        "entities": [
            {
                "id": 1,
                "name": "Fungoso",
                "entity_type": "character",
                "description": "El protagonista.",
                "_relevance": 1.0,
            },
        ],
        "relations": [
            {
                "id": "relation-1",
                "relation_type": "knows",
                "subject_id": 1,
                "target_id": 2,
            },
        ],
        "events": [],
        "items": [],
        "item_instances": [],
        "resources": [],
        "resource_balances": [],
    }

    context = builder._build_text_context(
        result
    )

    assert "Fungoso" in context


def test_context_builder_selected_context_respects_budget():
    builder = ContextBuilder(
        max_context_chars=120,
    )

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert len(result["context"]) <= 120


def test_context_builder_does_not_cut_lines_in_half():
    builder = ContextBuilder(
        max_context_chars=70,
    )

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    context = result["context"]

    for line in context.splitlines():
        assert line.strip() != ""


def test_context_builder_skips_oversized_candidate_and_continues():
    builder = ContextBuilder(
        max_context_chars=100,
    )

    result = {
        "query": "Fungoso",
        "entities": [
            {
                "id": 1,
                "name": "X" * 200,
                "entity_type": "character",
                "description": "",
            },
            {
                "id": 2,
                "name": "Fungoso",
                "entity_type": "character",
                "description": "",
            },
        ],
        "relations": [],
        "events": [],
        "items": [],
        "item_instances": [],
        "resources": [],
        "resource_balances": [],
    }

    context = builder._build_text_context(
        result
    )

    assert "Fungoso" in context
    assert "X" * 200 not in context


# ============================================================
# INTERNAL FIELD SAFETY
# ============================================================


def test_context_builder_strips_internal_entity_fields():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    for entity in result["entities"]:
        assert "_relevance" not in entity
        assert "_depth" not in entity


def test_context_builder_does_not_leak_internal_fields_into_text():
    builder = ContextBuilder()

    result = builder.build(
        build_world(),
        "Fungoso",
    )

    assert "_relevance" not in result["context"]
    assert "_depth" not in result["context"]


# ============================================================
# CATEGORY HEADER SAFETY
# ============================================================


def test_context_builder_known_category_header():
    assert (
        ContextBuilder._category_header(
            "entities"
        )
        == "[ENTIDADES]"
    )

    assert (
        ContextBuilder._category_header(
            "relations"
        )
        == "[RELACIONES]"
    )

    assert (
        ContextBuilder._category_header(
            "events"
        )
        == "[EVENTOS]"
    )


def test_context_builder_unknown_category_header_is_deterministic():
    assert (
        ContextBuilder._category_header(
            "unknown_category"
        )
        == "[UNKNOWN_CATEGORY]"
    )


def test_context_builder_builds_structured_context_data():
    builder = ContextBuilder()

    result = builder._build_context_data(
        build_world(),
        "Fungoso",
    )

    assert result["query"] == "Fungoso"

    assert "context" not in result

    names = {
        entity["name"]
        for entity in result["entities"]
    }

    assert "Fungoso" in names
    assert "Goblin" in names

    assert len(result["relations"]) == 1
    assert len(result["events"]) == 1

def test_context_builder_structured_data_is_not_limited_by_text_budget():
    builder = ContextBuilder(
        max_context_chars=1,
    )

    result = builder._build_context_data(
        build_world(),
        "Fungoso",
    )

    names = {
        entity["name"]
        for entity in result["entities"]
    }

    assert "Fungoso" in names
    assert "Goblin" in names

def test_context_builder_uses_provided_context_ranker():
    ranker = ContextRanker()

    builder = ContextBuilder(
        memory_search_service=MemorySearchService(),
        ranker=ranker,
    )

    assert builder.ranker is ranker

def test_context_builder_rejects_invalid_context_ranker():
    with pytest.raises(
        TypeError,
        match="ranker must be a ContextRanker",
    ):
        ContextBuilder(
            memory_search_service=MemorySearchService(),
            ranker=object(),
        )