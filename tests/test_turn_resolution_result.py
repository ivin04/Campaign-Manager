from dataclasses import FrozenInstanceError

import pytest

from models.operation_result import (
    OperationResult,
    OperationStatus,
)
from models.turn_resolution_result import (
    TurnResolutionResult,
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
        context="[ENTIDADES]",
    )


def make_success():
    return OperationResult(
        status=OperationStatus.SUCCESS,
        message="ok",
    )


def make_failure():
    return OperationResult(
        status=OperationStatus.INVALID,
        message="invalid",
    )


def test_result_is_frozen():

    result = make_result()

    with pytest.raises(
        FrozenInstanceError
    ):
        result.narrative = "otra cosa"


def test_response_is_alias_for_narrative():

    result = make_result()

    assert result.response == result.narrative


def test_world_changed_is_false_without_operations():

    result = make_result()

    assert result.world_changed is False


def test_world_changed_is_true_when_operation_succeeds():

    result = make_result(
        operation_results=(
            make_success(),
        )
    )

    assert result.world_changed is True


def test_world_changed_is_false_when_all_operations_fail():

    result = make_result(
        operation_results=(
            make_failure(),
        )
    )

    assert result.world_changed is False


def test_all_operations_succeeded_is_true_without_operations():

    result = make_result()

    assert result.all_operations_succeeded is True


def test_all_operations_succeeded_is_true_when_all_succeed():

    result = make_result(
        operation_results=(
            make_success(),
            make_success(),
        )
    )

    assert result.all_operations_succeeded is True


def test_all_operations_succeeded_is_false_when_one_fails():

    result = make_result(
        operation_results=(
            make_success(),
            make_failure(),
        )
    )

    assert result.all_operations_succeeded is False


def test_operation_count():

    result = make_result(
        operations=(
            object(),
            object(),
        )
    )

    assert result.operation_count == 2


def test_successful_operation_count():

    result = make_result(
        operation_results=(
            make_success(),
            make_failure(),
            make_success(),
        )
    )

    assert result.successful_operation_count == 2


def test_failed_operation_count():

    result = make_result(
        operation_results=(
            make_success(),
            make_failure(),
            make_failure(),
        )
    )

    assert result.failed_operation_count == 2