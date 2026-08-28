from models.character_state import CharacterState
from models.operation_result import (
    OperationResult,
    OperationStatus,
)
from operations.character_operations import (
    ChangeCharacterHpOperation,
)
from services.character_applier import (
    CharacterApplier,
    CharacterApplierError,
)


class RecordingCharacterService:

    def __init__(self):
        self.calls = []

    def change_hp(
        self,
        *,
        entity_id,
        amount,
    ):
        self.calls.append(
            (
                entity_id,
                amount,
            )
        )

        return CharacterState(
            entity_id=entity_id,
            current_hp=6,
            max_hp=10,
        )


def test_change_hp_operation_is_applied():

    service = RecordingCharacterService()

    applier = CharacterApplier(service)

    operation = ChangeCharacterHpOperation(
        entity_id=1,
        amount=-4,
    )

    result = applier.apply(operation)

    assert service.calls == [
        (1, -4),
    ]

    assert isinstance(
        result,
        OperationResult,
    )

    assert result.status == OperationStatus.SUCCESS
    assert result.success is True
    assert result.changed is True

    assert result.operation == operation

    assert result.data == {
        "entity_id": 1,
        "current_hp": 6,
    }

def test_unsupported_character_operation_is_rejected():

    service = RecordingCharacterService()

    applier = CharacterApplier(service)

    class UnsupportedOperation:
        pass

    try:
        applier.apply(
            UnsupportedOperation()
        )
    except CharacterApplierError as exc:
        assert str(exc) == (
            "unsupported character operation: "
            "UnsupportedOperation"
        )
    else:
        raise AssertionError(
            "Expected CharacterApplierError"
        )


def test_character_service_error_is_wrapped():

    class FailingCharacterService:

        def change_hp(
            self,
            *,
            entity_id,
            amount,
        ):
            raise CharacterServiceError(
                "character failure"
            )

    from services.character_service import (
        CharacterServiceError,
    )

    applier = CharacterApplier(
        FailingCharacterService()
    )

    operation = ChangeCharacterHpOperation(
        entity_id=1,
        amount=-4,
    )

    try:
        applier.apply(operation)
    except CharacterApplierError as exc:
        assert str(exc) == "character failure"
    else:
        raise AssertionError(
            "Expected CharacterApplierError"
        )


def test_apply_change_character_hp_passes_connection():
    from operations.character_operations import (
        ChangeCharacterHpOperation,
    )
    from services.character_applier import (
        CharacterApplier,
    )

    class RecordingCharacterService:

        def __init__(self):
            self.calls = []

        def change_hp(
            self,
            entity_id,
            amount,
            *,
            conn=None,
        ):
            self.calls.append(
                (
                    entity_id,
                    amount,
                    conn,
                )
            )

            return type(
                "Character",
                (),
                {
                    "current_hp": 15,
                },
            )()

    character_service = RecordingCharacterService()

    applier = CharacterApplier(
        character_service=character_service,
    )

    connection = object()

    operation = ChangeCharacterHpOperation(
        entity_id=7,
        amount=-5,
    )

    result = applier.apply(
        operation,
        conn=connection,
    )

    assert character_service.calls == [
        (
            7,
            -5,
            connection,
        )
    ]

    assert isinstance(
        result,
        OperationResult,
    )

    assert result.status == OperationStatus.SUCCESS
    assert result.success is True
    assert result.changed is True

    assert result.operation == operation

    assert result.data == {
        "entity_id": 7,
        "current_hp": 15,
    }