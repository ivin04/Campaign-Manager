import copy
import database

from models.entity import Entity
from models.world_state import WorldState

from services.world_service import WorldService

from repositories.world_repository import WorldRepository

from models.operation_result import (
    OperationResult,
    OperationStatus,
)

from operations.world_operations import CreateEntityOperation

from database import init_db

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
        self.called = False
        self.world = None
        self.operation = None

    def apply(self, world, operation):
        self.called = True
        self.world = world
        self.operation = operation

        return OperationResult(
            status=OperationStatus.SUCCESS,
            message="fake success",
            operation=operation,
        )

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

    assert result.status == OperationStatus.SUCCESS
    assert result.operation is operation

    assert applier.called is True
    assert applier.world is service.world
    assert applier.operation is operation

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

    assert result.status == OperationStatus.SUCCESS
    assert result.operation is operation

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

def test_apply_and_save_does_not_leave_memory_modified_when_save_fails(
    monkeypatch,
):
    service = WorldService()

    original_entities = dict(service.world.entities)

    def failing_save():
        raise RuntimeError("Database failure")

    monkeypatch.setattr(service, "save", failing_save)

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    try:
        service.apply_and_save(operation)
    except RuntimeError:
        pass

    assert service.world.entities == original_entities

def test_apply_and_save_does_not_save_when_apply_fails(
    monkeypatch,
):
    service = WorldService()

    original_world = copy.deepcopy(service.world)

    save_called = False

    def fake_save():
        nonlocal save_called
        save_called = True

    def fake_apply(operation):
        return OperationResult(
            status=OperationStatus.INVALID,
            message="Operation failed",
        )

    monkeypatch.setattr(service, "save", fake_save)
    monkeypatch.setattr(service, "apply", fake_apply)

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    result = service.apply_and_save(operation)

    assert result.success is False
    assert save_called is False
    assert service.world == original_world

def test_load_replaces_current_world_completely(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()

        repository = WorldRepository()

        # --------------------------------------------------------
        # Estado que realmente existe en SQLite
        # --------------------------------------------------------

        persisted_entity = Entity(
            id=1,
            name="Goblin",
            entity_type="creature",
        )

        persisted_world = WorldState(
            entities={
                1: persisted_entity,
            }
        )

        repository.save_world(persisted_world)

        # --------------------------------------------------------
        # Servicio con estado diferente en memoria
        # --------------------------------------------------------

        service = WorldService(
            repository=repository,
        )

        stale_entity = Entity(
            id=99,
            name="Entidad vieja",
            entity_type="character",
        )

        service.world = WorldState(
            entities={
                99: stale_entity,
            }
        )

        # --------------------------------------------------------
        # LOAD
        # --------------------------------------------------------

        loaded = service.load()

        # --------------------------------------------------------
        # Debe coincidir exactamente con SQLite
        # --------------------------------------------------------

        assert loaded == persisted_world
        assert service.world == persisted_world

        # La entidad antigua NO puede sobrevivir.
        assert 99 not in service.world.entities

        # La persistida sí.
        assert 1 in service.world.entities

    finally:
        database.DB_PATH = original_db_path