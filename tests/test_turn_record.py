import pytest

from models.turn_record import TurnRecord


def test_turn_record_accepts_consistent_operation_counts():
    record = TurnRecord(
        operation_count=3,
        successful_operation_count=2,
        failed_operation_count=1,
        all_operations_succeeded=False,
    )

    assert record.operation_count == 3


def test_turn_record_accepts_all_successful_operations():
    record = TurnRecord(
        operation_count=3,
        successful_operation_count=3,
        failed_operation_count=0,
        all_operations_succeeded=True,
    )

    assert record.all_operations_succeeded is True


def test_turn_record_rejects_invalid_session_id_type():
    with pytest.raises(TypeError):
        TurnRecord(
            session_id="1",
        )


def test_turn_record_rejects_invalid_operation_count_type():
    with pytest.raises(TypeError):
        TurnRecord(
            operation_count="1",
        )


def test_turn_record_rejects_negative_operation_count():
    with pytest.raises(ValueError):
        TurnRecord(
            operation_count=-1,
        )


def test_turn_record_rejects_negative_successful_operation_count():
    with pytest.raises(ValueError):
        TurnRecord(
            successful_operation_count=-1,
        )


def test_turn_record_rejects_negative_failed_operation_count():
    with pytest.raises(ValueError):
        TurnRecord(
            failed_operation_count=-1,
        )


def test_turn_record_rejects_inconsistent_operation_counts():
    with pytest.raises(ValueError):
        TurnRecord(
            operation_count=3,
            successful_operation_count=1,
            failed_operation_count=1,
            all_operations_succeeded=False,
        )


def test_turn_record_rejects_inconsistent_success_flag():
    with pytest.raises(ValueError):
        TurnRecord(
            operation_count=2,
            successful_operation_count=1,
            failed_operation_count=1,
            all_operations_succeeded=True,
        )


def test_turn_record_rejects_false_success_flag_when_nothing_failed():
    with pytest.raises(ValueError):
        TurnRecord(
            operation_count=2,
            successful_operation_count=2,
            failed_operation_count=0,
            all_operations_succeeded=False,
        )


def test_turn_record_rejects_boolean_operation_count():
    with pytest.raises(TypeError):
        TurnRecord(
            operation_count=True,
        )


def test_turn_record_rejects_invalid_created_at_type():
    with pytest.raises(TypeError):
        TurnRecord(
            created_at=123,
        )

def test_turn_record_accepts_valid_version():
    record = TurnRecord(
        version=2,
    )

    assert record.version == 2


def test_turn_record_rejects_invalid_version_type():
    with pytest.raises(TypeError):
        TurnRecord(
            version="1",
        )


def test_turn_record_rejects_boolean_version():
    with pytest.raises(TypeError):
        TurnRecord(
            version=True,
        )


def test_turn_record_rejects_zero_version():
    with pytest.raises(ValueError):
        TurnRecord(
            version=0,
        )


def test_turn_record_rejects_negative_version():
    with pytest.raises(ValueError):
        TurnRecord(
            version=-1,
        )


def test_turn_record_accepts_active_status():
    record = TurnRecord(
        status="active",
    )

    assert record.status == "active"


def test_turn_record_accepts_superseded_status():
    record = TurnRecord(
        status="superseded",
    )

    assert record.status == "superseded"


def test_turn_record_rejects_invalid_status_type():
    with pytest.raises(TypeError):
        TurnRecord(
            status=1,
        )


def test_turn_record_rejects_unknown_status():
    with pytest.raises(ValueError):
        TurnRecord(
            status="invalid",
        )


def test_turn_record_rejects_empty_status():
    with pytest.raises(ValueError):
        TurnRecord(
            status="",
        )