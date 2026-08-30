import pytest
import database

from models.entity import Entity
from models.world_state import WorldState

from services.world_service import WorldService

from repositories.world_repository import WorldRepository

from models.operation_result import (
    OperationResult,
    OperationStatus,
)

from operations.world_operations import (
    CreateEntityOperation,
    CreateItemOperation,
    CreateItemInstanceOperation,
)

from operations.operation_reference import OperationReference
from operations.referenced_operation import ReferencedOperation

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

def test_apply_returns_success_result_for_successful_operation():

    service = WorldService()

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    result = service.apply(operation)

    assert result.success is True
    assert result.status == OperationStatus.SUCCESS
    assert result.operation == operation

def test_apply_returns_failure_result_for_invalid_operation():

    service = WorldService()

    operation = CreateEntityOperation(
        name="",
        entity_type="character",
    )

    result = service.apply(operation)

    assert result.success is False
    assert result.status != OperationStatus.SUCCESS

def test_apply_operations_applies_all_operations_without_saving():
    repository = FakeRepository()
    applier = FakeApplier()

    service = WorldService(
        repository=repository,
        applier=applier,
    )

    operations = [
        CreateEntityOperation(
            name="Fungoso",
            entity_type="character",
        ),
        CreateEntityOperation(
            name="Goblin",
            entity_type="creature",
        ),
    ]

    result = service.apply_operations(
        operations
    )

    assert result.success is True
    assert len(result.results) == 2

    assert repository.save_calls == 0

    assert service.world is result.world

def test_apply_operations_rolls_back_when_one_operation_fails(
    monkeypatch,
):
    service = WorldService()

    original_world = service.world

    operation_1 = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    operation_2 = CreateEntityOperation(
        name="Goblin",
        entity_type="creature",
    )

    call_count = 0

    def fake_apply(operation):
        nonlocal call_count

        call_count += 1

        if call_count == 1:
            service.world.entities[1] = Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
            )

            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Success",
                operation=operation,
            )

        return OperationResult(
            status=OperationStatus.INVALID,
            message="Operation failed",
            operation=operation,
        )

    monkeypatch.setattr(
        service,
        "apply",
        fake_apply,
    )

    result = service.apply_operations(
        [
            operation_1,
            operation_2,
        ]
    )

    assert result.success is False

    assert service.world is original_world
    assert service.world.entities == {}

def test_apply_operations_restores_original_world_when_apply_raises(
    monkeypatch,
):
    service = WorldService()

    original_world = service.world

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    def failing_apply(operation):
        service.world.entities[1] = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        raise RuntimeError("Unexpected failure")

    monkeypatch.setattr(
        service,
        "apply",
        failing_apply,
    )

    try:
        service.apply_operations(
            [operation]
        )
    except RuntimeError:
        pass

    assert service.world is original_world
    assert service.world.entities == {}

def test_apply_operations_and_save_persists_successful_operations(
    monkeypatch,
):
    service = WorldService()

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    original_save = service.repository.save_world
    save_calls = []

    def spy_save_world(world):
        save_calls.append(world)
        return original_save(world)

    monkeypatch.setattr(
        service.repository,
        "save_world",
        spy_save_world,
    )

    result = service.apply_operations_and_save(
        [operation]
    )

    assert result.success is True
    assert len(save_calls) == 1
    assert save_calls[0] is service.get_world()

def test_apply_operations_and_save_restores_original_world_when_save_fails(
    monkeypatch,
):
    service = WorldService()

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    original_world = service.get_world()

    def failing_save_world(world):
        raise RuntimeError("database failed")

    monkeypatch.setattr(
        service.repository,
        "save_world",
        failing_save_world,
    )

    with pytest.raises(
        RuntimeError,
        match="database failed",
    ):
        service.apply_operations_and_save(
            [operation]
        )

    assert service.get_world() is original_world

def test_apply_operations_and_save_does_not_save_when_operation_fails(
    monkeypatch,
):
    service = WorldService()

    operation = CreateEntityOperation(
        name="Fungoso",
        entity_type="character",
    )

    original_world = service.get_world()

    save_called = False

    def spy_save_world(world):
        nonlocal save_called
        save_called = True

    def failing_apply(
        world,
        operation,
    ):
        return OperationResult(
            status=OperationStatus.INVALID,
            message="operation failed",
            operation=operation,
        )

    monkeypatch.setattr(
        service.repository,
        "save_world",
        spy_save_world,
    )

    monkeypatch.setattr(
        service.applier,
        "apply",
        failing_apply,
    )

    result = service.apply_operations_and_save(
        [operation]
    )

    assert result.success is False
    assert save_called is False
    assert service.get_world() is original_world
    assert result.changed is False
    assert len(result.results) == 1

def test_apply_operations_and_save_does_not_save_when_there_are_no_operations(
    monkeypatch,
):
    service = WorldService()

    save_called = False

    def spy_save_world(world):
        nonlocal save_called
        save_called = True

    monkeypatch.setattr(
        service.repository,
        "save_world",
        spy_save_world,
    )

    result = service.apply_operations_and_save(
        []
    )

    assert result.success is True
    assert result.changed is False
    assert result.results == ()
    assert save_called is False

def test_apply_operations_and_save_marks_world_as_changed(
    monkeypatch,
):
    service = WorldService()

    operation = CreateEntityOperation(
        name="Aldric",
        entity_type="character",
    )

    save_calls = []

    def spy_save_world(world):
        save_calls.append(world)

    monkeypatch.setattr(
        service.repository,
        "save_world",
        spy_save_world,
    )

    result = service.apply_operations_and_save(
        [operation]
    )

    assert result.success is True
    assert result.changed is True
    assert len(result.results) == 1
    assert result.results[0].success is True

    assert len(save_calls) == 1

def test_apply_turn_operations_rolls_back_when_character_operation_fails(
    monkeypatch,
):
    from services.character_applier import (
        CharacterApplierError,
    )

    class RecordingConnection:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

    connection = RecordingConnection()

    class ConnectionContext:

        def __enter__(self):
            return connection

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            if exc_type is None:
                connection.committed = True
            else:
                connection.rolled_back = True

            return False

    monkeypatch.setattr(
        "services.world_service.get_conn",
        lambda: ConnectionContext(),
    )

    class FailingCharacterApplier:

        def apply(
            self,
            operation,
            *,
            conn=None,
        ):
            raise CharacterApplierError(
                "character failure"
            )

    service = WorldService(
        character_applier=FailingCharacterApplier(),
    )

    original_world = service.world

    with pytest.raises(
        CharacterApplierError,
        match="character failure",
    ):
        service.apply_turn_operations(
            world_operations=(),
            character_operations=(object(),),
        )

    assert service.world is original_world
    assert connection.committed is False
    assert connection.rolled_back is True

def test_apply_turn_operations_rolls_back_when_world_operation_fails(
    monkeypatch,
):
    class RecordingConnection:
        def __init__(self):
            self.committed = False
            self.rolled_back = False

    connection = RecordingConnection()

    class ConnectionContext:

        def __enter__(self):
            return connection

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            if exc_type is None:
                connection.committed = True
            else:
                connection.rolled_back = True

            return False

    monkeypatch.setattr(
        "services.world_service.get_conn",
        lambda: ConnectionContext(),
    )

    service = WorldService()

    original_world = service.world

    class FailingWorldApplier:

        def apply(
            self,
            world,
            operation,
        ):
            return OperationResult(
                status=OperationStatus.INVALID,
                message="world operation failed",
                operation=operation,
            )

    service.applier = FailingWorldApplier()

    result = service.apply_turn_operations(
        world_operations=(object(),),
        character_operations=(),
    )

    assert len(result) == 1
    assert result[0].success is False
    assert result[0].status == OperationStatus.INVALID

    assert service.world is original_world

    assert connection.committed is False
    assert connection.rolled_back is True

def test_apply_turn_operations_rolls_back_when_character_operation_returns_failure(
    isolated_database,
):
    from models.operation_result import (
        OperationResult,
        OperationStatus,
    )
    from models.world_state import WorldState
    from operations.character_operations import (
        ChangeCharacterHpOperation,
    )
    from services.character_applier import (
        CharacterApplier,
    )
    from services.world_service import (
        WorldService,
    )

    class FailingCharacterApplier:

        def apply(
            self,
            operation,
            *,
            conn=None,
        ):
            return OperationResult(
                status=OperationStatus.INVALID,
                message="character operation failed",
                operation=operation,
            )

    service = WorldService(
        character_applier=FailingCharacterApplier(),
    )

    original_world = service.world

    operation = ChangeCharacterHpOperation(
        entity_id=1,
        amount=-5,
    )

    results = service.apply_turn_operations(
        world_operations=[],
        character_operations=[
            operation,
        ],
    )

    assert len(results) == 1

    assert results[0].success is False

    assert service.world is original_world

def test_apply_operations_resolves_generated_item_reference():
    service = WorldService()

    result = service.apply_operations(
        [
            ReferencedOperation(
                operation=CreateItemOperation(
                    name="Espada oxidada",
                ),
                ref="sword",
            ),
            CreateItemInstanceOperation(
                item_id=OperationReference(
                    "sword"
                ),
                owner_id=None,
            ),
        ]
    )

    assert result.success is True
    assert result.changed is True
    assert len(result.results) == 2

    assert len(service.world.items) == 1
    assert len(service.world.item_instances) == 1

    item = next(
        iter(service.world.items.values())
    )

    instance = next(
        iter(
            service.world.item_instances.values()
        )
    )

    assert instance.item_id == item.id

def test_apply_operations_rejects_unknown_operation_reference():
    service = WorldService()

    with pytest.raises(
        ValueError,
        match=r"Unknown operation reference: \$missing",
    ):
        service.apply_operations(
            [
                CreateItemInstanceOperation(
                    item_id=OperationReference(
                        "missing"
                    ),
                ),
            ]
        )

    assert service.world.items == {}
    assert service.world.item_instances == {}

def test_apply_turn_operations_resolves_generated_character_reference(
    monkeypatch,
):
    from models.operation_result import (
        OperationResult,
        OperationStatus,
    )

    from operations.character_operations import (
        ChangeCharacterHpOperation,
    )

    class RecordingCharacterApplier:
        def __init__(self):
            self.operations = []

        def apply(
            self,
            operation,
            *,
            conn=None,
        ):
            self.operations.append(operation)

            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Character HP changed",
                operation=operation,
                data={
                    "entity_id": operation.entity_id,
                    "current_hp": 8,
                },
            )

    character_applier = RecordingCharacterApplier()

    service = WorldService(
        character_applier=character_applier,
    )

    create_operation = CreateEntityOperation(
        name="Aldric",
        entity_type="character",
    )

    referenced_create = ReferencedOperation(
        operation=create_operation,
        ref="aldric",
    )

    hp_operation = ChangeCharacterHpOperation(
        entity_id=OperationReference("aldric"),
        amount=-2,
    )

    result = service.apply_turn_operations(
        world_operations=[
            referenced_create,
        ],
        character_operations=[
            hp_operation,
        ],
    )

    assert len(result) == 2

    assert result[0].success is True
    assert result[1].success is True

    assert len(character_applier.operations) == 1

    applied_operation = (
        character_applier.operations[0]
    )

    assert applied_operation.entity_id == 1
    assert applied_operation.amount == -2

def test_apply_operations_rejects_empty_operation_reference():
    service = WorldService()

    operation = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
        description="Mercader.",
        notes="",
        active=True,
    )

    referenced_operation = ReferencedOperation(
        operation=operation,
        ref="",
    )

    with pytest.raises(
        ValueError,
        match="Operation reference must not be empty",
    ):
        service.apply_operations(
            [
                referenced_operation,
            ]
        )

    assert service.world.entities == {}


def test_apply_operations_rejects_whitespace_operation_reference():
    service = WorldService()

    operation = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
        description="Mercader.",
        notes="",
        active=True,
    )

    referenced_operation = ReferencedOperation(
        operation=operation,
        ref="   ",
    )

    with pytest.raises(
        ValueError,
        match="Operation reference must not be empty",
    ):
        service.apply_operations(
            [
                referenced_operation,
            ]
        )

    assert service.world.entities == {}


def test_apply_operations_rejects_duplicate_operation_reference():
    service = WorldService()

    first_operation = CreateEntityOperation(
        name="Aldric",
        entity_type="npc",
        description="Primer mercader.",
        notes="",
        active=True,
    )

    second_operation = CreateEntityOperation(
        name="Brann",
        entity_type="npc",
        description="Segundo mercader.",
        notes="",
        active=True,
    )

    with pytest.raises(
        ValueError,
        match="Operation reference 'merchant' is already defined",
    ):
        service.apply_operations(
            [
                ReferencedOperation(
                    operation=first_operation,
                    ref="merchant",
                ),
                ReferencedOperation(
                    operation=second_operation,
                    ref="merchant",
                ),
            ]
        )

    assert service.world.entities == {}