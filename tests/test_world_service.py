from models.entity import Entity
from models.world_state import WorldState

from services.world_service import WorldService


class FakeRepository:

    def __init__(self, world=None):
        self.world = world or WorldState()
        self.saved_world = None
        self.load_calls = 0
        self.save_calls = 0

    def load_world(self):
        self.load_calls += 1
        return self.world

    def save_world(self, world):
        self.save_calls += 1
        self.saved_world = world

class FakeApplier:

    def __init__(self):
        self.calls = []

    def apply(self, world, operation):
        self.calls.append((world, operation))

def test_load_sets_current_world():

    world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
            )
        }
    )

    repository = FakeRepository(world)

    service = WorldService(
        repository=repository,
        applier=FakeApplier(),
    )

    loaded = service.load()

    assert loaded is world
    assert service.world is world
    assert repository.load_calls == 1

def test_save_persists_current_world():

    repository = FakeRepository()

    service = WorldService(
        repository=repository,
        applier=FakeApplier(),
    )

    service.world.entities[1] = Entity(
        id=1,
        name="Fungoso",
        entity_type="character",
    )

    service.save()

    assert repository.save_calls == 1
    assert repository.saved_world is service.world

def test_apply_delegates_to_applier():

    repository = FakeRepository()
    applier = FakeApplier()

    service = WorldService(
        repository=repository,
        applier=applier,
    )

    operation = object()

    result = service.apply(operation)

    assert result is service.world

    assert len(applier.calls) == 1

    applied_world, applied_operation = applier.calls[0]

    assert applied_world is service.world
    assert applied_operation is operation

def test_apply_does_not_save():

    repository = FakeRepository()
    applier = FakeApplier()

    service = WorldService(
        repository=repository,
        applier=applier,
    )

    service.apply(object())

    assert repository.save_calls == 0

def test_apply_and_save_applies_then_saves():

    repository = FakeRepository()
    applier = FakeApplier()

    service = WorldService(
        repository=repository,
        applier=applier,
    )

    operation = object()

    result = service.apply_and_save(operation)

    assert result is service.world

    assert len(applier.calls) == 1

    assert repository.save_calls == 1
    assert repository.saved_world is service.world

def test_get_world_returns_current_world():

    service = WorldService(
        repository=FakeRepository(),
        applier=FakeApplier(),
    )

    assert service.get_world() is service.world

def test_load_replaces_current_world():

    old_world = WorldState()

    new_world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
            )
        }
    )

    repository = FakeRepository(new_world)

    service = WorldService(
        repository=repository,
        applier=FakeApplier(),
    )

    service.world = old_world

    loaded = service.load()

    assert loaded is new_world
    assert service.world is new_world
    assert service.world is not old_world