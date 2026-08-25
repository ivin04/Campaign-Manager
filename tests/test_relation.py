from models.entity import Entity
from models.relation import Relation
from models.world_state import WorldState
from models.extraction import ExtractedFact

from operations.world_operations import (
    CreateRelationOperation,
    UpdateRelationOperation,
    RemoveRelationOperation,
)

from services.resolution import WorldResolver
from services.world_applier import WorldApplier


def build_world():
    return WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
            ),
            2: Entity(
                id=2,
                name="Neria",
                entity_type="character",
            ),
        },
        relations={},
    )

def build_resolver():
    world = build_world()

    world.relations["rel-1"] = Relation(
        id="rel-1",
        subject_id=1,
        relation_type="ALLIED_WITH",
        target_id=2,
    )

    return WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
        relations=world.relations,
    )


def test_resolve_relation_created():
    world = build_world()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "relation-1",
            "subject": "Fungoso",
            "relation_type": "ALLIED_WITH",
            "target": "Neria",
        },
    )

    resolver = WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
        relations=world.relations,
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, CreateRelationOperation)
    assert operation.relation_id == "relation-1"
    assert operation.subject_id == 1
    assert operation.relation_type == "ALLIED_WITH"
    assert operation.target_id == 2


def test_resolve_relation_rejects_unknown_subject():
    world = build_world()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "relation-1",
            "subject": "Unknown",
            "relation_type": "ALLIED_WITH",
            "target": "Neria",
        },
    )

    resolver = WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
        relations=world.relations,
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_relation_rejects_unknown_target():
    world = build_world()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "relation-1",
            "subject": "Fungoso",
            "relation_type": "ALLIED_WITH",
            "target": "Unknown",
        },
    )

    resolver = WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
        relations=world.relations,
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_resolve_relation_rejects_missing_relation_id():
    world = build_world()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "subject": "Fungoso",
            "relation_type": "ALLIED_WITH",
            "target": "Neria",
        },
    )

    resolver = WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
        relations=world.relations,
    )

    operations = resolver.resolve([fact])

    assert operations == []


def test_apply_create_relation():
    world = build_world()

    operation = CreateRelationOperation(
        relation_id="relation-1",
        subject_id=1,
        relation_type="ALLIED_WITH",
        target_id=2,
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert "relation-1" in world.relations

    relation = world.relations["relation-1"]

    assert relation.id == "relation-1"
    assert relation.subject_id == 1
    assert relation.relation_type == "ALLIED_WITH"
    assert relation.target_id == 2
    assert relation.active is True


def test_apply_create_relation_rejects_unknown_subject():
    world = build_world()

    operation = CreateRelationOperation(
        relation_id="relation-1",
        subject_id=999,
        relation_type="ALLIED_WITH",
        target_id=2,
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert world.relations == {}


def test_apply_create_relation_rejects_unknown_target():
    world = build_world()

    operation = CreateRelationOperation(
        relation_id="relation-1",
        subject_id=1,
        relation_type="ALLIED_WITH",
        target_id=999,
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert world.relations == {}


def test_apply_create_relation_does_not_overwrite_existing_relation():
    world = build_world()

    world.relations["relation-1"] = Relation(
        id="relation-1",
        subject_id="1",
        relation_type="HATES",
        target_id="2",
    )

    operation = CreateRelationOperation(
        relation_id="relation-1",
        subject_id=1,
        relation_type="ALLIED_WITH",
        target_id=2,
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    relation = world.relations["relation-1"]

    assert relation.relation_type == "HATES"


def test_apply_update_relation_metadata():
    world = build_world()

    world.relations["relation-1"] = Relation(
        id="relation-1",
        subject_id="1",
        relation_type="ALLIED_WITH",
        target_id="2",
        metadata={"strength": "weak"},
    )

    operation = UpdateRelationOperation(
        relation_id="relation-1",
        metadata={"strength": "strong"},
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    relation = world.relations["relation-1"]

    assert relation.metadata == {"strength": "strong"}


def test_apply_update_relation_active_state():
    world = build_world()

    world.relations["relation-1"] = Relation(
        id="relation-1",
        subject_id="1",
        relation_type="ALLIED_WITH",
        target_id="2",
        active=True,
    )

    operation = UpdateRelationOperation(
        relation_id="relation-1",
        active=False,
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert world.relations["relation-1"].active is False


def test_apply_remove_relation():
    world = build_world()

    world.relations["relation-1"] = Relation(
        id="relation-1",
        subject_id="1",
        relation_type="ALLIED_WITH",
        target_id="2",
        active=True,
    )

    operation = RemoveRelationOperation(
        relation_id="relation-1",
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert "relation-1" in world.relations
    assert world.relations["relation-1"].active is False


def test_apply_remove_relation_unknown_relation():
    world = build_world()

    operation = RemoveRelationOperation(
        relation_id="does-not-exist",
    )

    applier = WorldApplier()

    applier.apply(world, operation)

    assert world.relations == {}

def test_resolve_relation_changed_type():

    resolver = build_resolver()

    facts = [
        ExtractedFact(
            fact_type="RELATION_CHANGED",
            data={
                "relation_id": "rel-1",
                "relation_type": "enemy",
            },
        )
    ]

    operations = resolver.resolve(facts)

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(
        operation,
        UpdateRelationOperation,
    )

    assert operation.relation_id == "rel-1"
    assert operation.relation_type == "enemy"

def test_resolve_relation_changed_target():

    resolver = build_resolver()

    facts = [
        ExtractedFact(
            fact_type="RELATION_CHANGED",
            data={
                "relation_id": "rel-1",
                "target_id": "2",
            },
        )
    ]

    operations = resolver.resolve(facts)

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(
        operation,
        UpdateRelationOperation,
    )

    assert operation.relation_id == "rel-1"
    assert operation.target_id == 2

def test_resolve_relation_changed_rejects_empty_relation_id():

    resolver = build_resolver()

    facts = [
        ExtractedFact(
            fact_type="RELATION_CHANGED",
            data={
                "relation_id": "",
                "relation_type": "enemy",
            },
        )
    ]

    operations = resolver.resolve(facts)

    assert operations == []

def test_resolve_relation_changed_rejects_invalid_metadata():

    resolver = build_resolver()

    facts = [
        ExtractedFact(
            fact_type="RELATION_CHANGED",
            data={
                "relation_id": "rel-1",
                "metadata": "not-a-dict",
            },
        )
    ]

    operations = resolver.resolve(facts)

    assert operations == []

def test_resolve_relation_changed_rejects_invalid_active():

    resolver = build_resolver()

    facts = [
        ExtractedFact(
            fact_type="RELATION_CHANGED",
            data={
                "relation_id": "rel-1",
                "active": "false",
            },
        )
    ]

    operations = resolver.resolve(facts)

    assert operations == []

def build_resolver():
    world = build_world()

    return WorldResolver(
        entities=world.entities,
        items=world.items,
        item_instances=world.item_instances,
        resources=world.resources,
        resource_balances=world.resource_balances,
        relations=world.relations,
    )

def test_resolve_relation_created_rejects_invalid_relation_id_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": 123,
            "subject": "Fungoso",
            "relation_type": "enemy",
            "target": "Elric",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_rejects_invalid_relation_id_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": 123,
            "active": True,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_removed_rejects_invalid_relation_id_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_REMOVED",
        data={
            "relation_id": 123,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_rejects_blank_relation_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "   ",
            "active": True,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_created_rejects_invalid_relation_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "Fungoso",
            "relation_type": 123,
            "target": "Elric",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_created_rejects_blank_relation_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "Fungoso",
            "relation_type": "   ",
            "target": "Elric",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_rejects_blank_relation_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "relation_type": "   ",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_rejects_boolean_target_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "target_id": True,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_rejects_false_target_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "target_id": False,
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_converts_target_id_to_int():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "target_id": "2",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1
    assert operations[0].target_id == 2

def test_resolve_relation_created_accepts_metadata_dict():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "Fungoso",
            "relation_type": "enemy",
            "target": "Neria",
            "metadata": {
                "reason": "betrayal",
            },
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, CreateRelationOperation)
    assert operation.relation_id == "rel-1"
    assert operation.subject_id == 1
    assert operation.relation_type == "enemy"
    assert operation.target_id == 2
    assert operation.metadata == {
        "reason": "betrayal",
    }


def test_resolve_relation_created_accepts_empty_metadata():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "Fungoso",
            "relation_type": "enemy",
            "target": "Neria",
            "metadata": {},
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, CreateRelationOperation)
    assert operation.metadata == {}

def test_resolve_relation_changed_rejects_invalid_metadata():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "metadata": "invalid",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_created_rejects_invalid_subject_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": 123,
            "relation_type": "enemy",
            "target": "Neria",
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_relation_created_rejects_blank_subject():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "   ",
            "relation_type": "enemy",
            "target": "Neria",
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_relation_created_rejects_invalid_target_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "Fungoso",
            "relation_type": "enemy",
            "target": 123,
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_relation_created_rejects_blank_target():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CREATED",
        data={
            "relation_id": "rel-1",
            "subject": "Fungoso",
            "relation_type": "enemy",
            "target": "   ",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_removed():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_REMOVED",
        data={
            "relation_id": "rel-1",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(
        operation,
        RemoveRelationOperation,
    )

    assert operation.relation_id == "rel-1"


def test_resolve_relation_removed_rejects_empty_relation_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_REMOVED",
        data={
            "relation_id": "",
        },
    )

    assert resolver.resolve([fact]) == []


def test_resolve_relation_removed_rejects_blank_relation_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_REMOVED",
        data={
            "relation_id": "   ",
        },
    )

    assert resolver.resolve([fact]) == []

def test_resolve_relation_changed_rejects_no_changes():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []

def test_resolve_relation_changed_accepts_metadata_dict():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "relation_type": "enemy",
            "metadata": {
                "reason": "betrayal",
            },
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, UpdateRelationOperation)
    assert operation.relation_id == "rel-1"
    assert operation.relation_type == "enemy"
    assert operation.metadata == {
        "reason": "betrayal",
    }

def test_resolve_relation_changed_accepts_active_bool():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "active": False,
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, UpdateRelationOperation)
    assert operation.relation_id == "rel-1"
    assert operation.active is False

def test_resolve_relation_changed_rejects_invalid_active_type():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "active": 1,
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []

def test_resolve_relation_changed_accepts_empty_metadata():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "metadata": {},
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, UpdateRelationOperation)
    assert operation.relation_id == "rel-1"
    assert operation.metadata == {}

def test_resolve_relation_changed_rejects_explicit_none_metadata_only():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_CHANGED",
        data={
            "relation_id": "rel-1",
            "metadata": None,
        },
    )

    operations = resolver.resolve([fact])

    assert operations == []

def test_resolve_relation_removed_accepts_valid_relation_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_REMOVED",
        data={
            "relation_id": "rel-1",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, RemoveRelationOperation)
    assert operation.relation_id == "rel-1"

def test_resolve_relation_removed_preserves_relation_id():
    resolver = build_resolver()

    fact = ExtractedFact(
        fact_type="RELATION_REMOVED",
        data={
            "relation_id": " relation-1 ",
        },
    )

    operations = resolver.resolve([fact])

    assert len(operations) == 1

    operation = operations[0]

    assert isinstance(operation, RemoveRelationOperation)
    assert operation.relation_id == " relation-1 "