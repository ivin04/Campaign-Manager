from models.world_state import WorldState
from operations.world_operations import CreateEntityOperation
from services.world_applier import WorldApplier


def test_create_entity():
    world = WorldState()
    applier = WorldApplier()

    operation = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
        description="Un minero viejo.",
        notes="Sabe algo sobre las desapariciones.",
    )

    applier.apply(world, operation)

    assert len(world.entities) == 1

    entity = world.entities[1]

    assert entity.id == 1
    assert entity.name == "Aldric"
    assert entity.entity_type == "npc"
    assert entity.description == "Un minero viejo."
    assert entity.notes == "Sabe algo sobre las desapariciones."
    assert entity.active is True

def test_create_entity_generates_next_id():
    world = WorldState()

    applier = WorldApplier()

    first = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
    )

    second = CreateEntityOperation(
        name="Mara",
        entity_type="npc",
    )

    applier.apply(world, first)
    applier.apply(world, second)

    assert len(world.entities) == 2

    assert world.entities[1].name == "Aldric"
    assert world.entities[2].name == "Mara"

def test_create_entity_does_not_create_duplicate():
    world = WorldState()
    applier = WorldApplier()

    first = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
    )

    duplicate = CreateEntityOperation(
        name="aldric",
        entity_type="npc",
    )

    applier.apply(world, first)
    applier.apply(world, duplicate)

    assert len(world.entities) == 1
    assert world.entities[1].name == "Aldric"