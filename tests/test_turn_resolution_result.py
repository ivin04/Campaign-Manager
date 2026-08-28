from __future__ import annotations

import pytest

from models.operation_result import OperationResult
from models.turn_resolution_result import TurnResolutionResult
from models.operation_result import OperationStatus

from models.turn_resolution_result import (
    TurnResolutionResult,
)
from operations.character_operations import (
    ChangeCharacterHpOperation,
)

from operations.world_operations import (
    WorldOperation,
)


def make_success() -> OperationResult:
    return OperationResult(
        status=OperationStatus.SUCCESS,
        message="ok",
        operation=None,
    )


def make_failure() -> OperationResult:
    return OperationResult(
        status=OperationStatus.INVALID,
        message="invalid",
        operation=None,
    )


def make_result(
    *,
    operation_results=(),
    operations=(),
):
    return TurnResolutionResult(
        player_input="Exploro la taberna.",
        narrative="Encuentras una taberna silenciosa.",
        operations=operations,
        operation_results=operation_results,
    )


def test_result_is_frozen():

    result = make_result()

    with pytest.raises(
        AttributeError
    ):
        result.narrative = "otra cosa"


def test_response_is_alias_for_narrative():

    result = make_result()

    assert result.response == result.narrative


def test_world_changed_is_false_without_operations():

    result = make_result()

    assert result.world_changed is False


def test_world_changed_is_true_when_all_operations_succeed():

    operations = (
        object(),
    )

    result = make_result(
        operations=operations,
        operation_results=(
            make_success(),
        ),
    )

    assert result.world_changed is True


def test_world_changed_is_false_when_all_operations_fail():

    operations = (
        object(),
    )

    result = make_result(
        operations=operations,
        operation_results=(
            make_failure(),
        ),
    )

    assert result.world_changed is False


def test_world_changed_is_false_when_any_operation_fails():

    """
    La aplicación de operaciones es atómica.

    Si una operación falla, el WorldState completo
    debe conservarse sin cambios.

    Por tanto, aunque alguna operación individual
    haya tenido éxito, el turno NO se considera
    un cambio confirmado.
    """

    operations = (
        object(),
        object(),
    )

    result = make_result(
        operations=operations,
        operation_results=(
            make_success(),
            make_failure(),
        ),
    )

    assert result.world_changed is False


def test_world_changed_is_false_when_result_count_does_not_match_operations():

    """
    Un resultado incompleto no puede considerarse
    un cambio confirmado.
    """

    operations = (
        object(),
        object(),
    )

    result = make_result(
        operations=operations,
        operation_results=(
            make_success(),
        ),
    )

    assert result.world_changed is False


def test_all_operations_succeeded_is_true_without_operations():

    result = make_result()

    assert result.all_operations_succeeded is True


def test_all_operations_succeeded_is_true_when_all_succeed():

    result = make_result(
        operations=(
            object(),
            object(),
        ),
        operation_results=(
            make_success(),
            make_success(),
        ),
    )

    assert result.all_operations_succeeded is True


def test_all_operations_succeeded_is_false_when_one_fails():

    result = make_result(
        operations=(
            object(),
            object(),
        ),
        operation_results=(
            make_success(),
            make_failure(),
        ),
    )

    assert result.all_operations_succeeded is False


def test_operation_count():

    result = make_result(
        operations=(
            object(),
            object(),
        ),
    )

    assert result.operation_count == 2


def test_successful_operation_count():

    result = make_result(
        operation_results=(
            make_success(),
            make_failure(),
            make_success(),
        ),
    )

    assert result.successful_operation_count == 2


def test_failed_operation_count():

    result = make_result(
        operation_results=(
            make_success(),
            make_failure(),
            make_failure(),
        ),
    )

    assert result.failed_operation_count == 2

def test_world_changed_is_false_when_operation_is_no_change():

    result = make_result(
        operations=(
            object(),
        ),
        operation_results=(
            OperationResult(
                status=OperationStatus.NO_CHANGE,
                message="already in requested state",
            ),
        ),
    )

    assert result.world_changed is False

def test_world_changed_is_false_when_operation_is_no_change_with_unchanged_message():

    result = make_result(
        operations=(
            object(),
        ),
        operation_results=(
            OperationResult(
                status=OperationStatus.NO_CHANGE,
                message="unchanged",
            ),
        ),
    )

    assert result.world_changed is False

def test_turn_resolution_result_supports_character_operations():

    operation = ChangeCharacterHpOperation(
        entity_id=1,
        amount=-5,
    )

    result = TurnResolutionResult(
        player_input="Ataco al goblin.",
        narrative="El goblin te hiere.",
        character_operations=(
            operation,
        ),
    )

    assert result.character_operations == (
        operation,
    )

    assert result.operations == ()

def test_operation_count_includes_character_operations():

    world_operation = object()

    character_operation = object()

    result = TurnResolutionResult(
        player_input="Ataco.",
        narrative="El golpe impacta.",
        operations=(world_operation,),
        character_operations=(
            character_operation,
        ),
    )

    assert result.operation_count == 2

def test_world_changed_is_true_for_character_operation():
    result = TurnResolutionResult(
        player_input="Ataco al goblin.",
        narrative="El golpe alcanza al goblin.",
        character_operations=(
            ChangeCharacterHpOperation(
                entity_id=1,
                amount=-5,
            ),
        ),
        operation_results=(
            type(
                "Result",
                (),
                {
                    "success": True,
                    "changed": True,
                },
            )(),
        ),
    )

    assert result.world_changed is True

def test_world_changed_requires_results_for_all_operations():
    result = TurnResolutionResult(
        player_input="Ataco.",
        narrative="El golpe impacta.",
        operations=(
            WorldOperation(),
        ),
        character_operations=(
            ChangeCharacterHpOperation(
                entity_id=1,
                amount=-5,
            ),
        ),
        operation_results=(
            type(
                "Result",
                (),
                {
                    "success": True,
                    "changed": True,
                },
            )(),
        ),
    )

    assert result.world_changed is False