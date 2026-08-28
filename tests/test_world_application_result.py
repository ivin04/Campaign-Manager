from models.operation_result import (
    OperationResult,
    OperationStatus,
)
from models.world_application_result import (
    WorldApplicationResult,
)


def test_world_application_result_is_frozen():
    result = WorldApplicationResult(
        success=True,
        changed=True,
    )

    try:
        result.changed = False
    except AttributeError:
        pass
    else:
        raise AssertionError(
            "WorldApplicationResult must be frozen"
        )


def test_world_application_result_counts_operations():

    results = (
        OperationResult(
            status=OperationStatus.SUCCESS,
        ),
        OperationResult(
            status=OperationStatus.INVALID,
        ),
        OperationResult(
            status=OperationStatus.SUCCESS,
        ),
    )

    result = WorldApplicationResult(
        success=False,
        changed=False,
        results=results,
    )

    assert result.operation_count == 3
    assert result.successful_operation_count == 2
    assert result.failed_operation_count == 1