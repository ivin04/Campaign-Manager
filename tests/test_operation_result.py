def test_no_change_operation_result_is_successful_but_not_changed():
    from models.operation_result import (
        OperationResult,
        OperationStatus,
    )

    result = OperationResult(
        status=OperationStatus.NO_CHANGE,
        message="Nothing changed.",
    )

    assert result.success is True
    assert result.changed is False