import pytest

from models.turn_record import TurnRecord
from repositories.turn_repository import TurnRepository
from repositories.campaign_repository import CampaignRepository

def test_save_turn_and_get_turn(
    isolated_database,
):
    repository = TurnRepository()

    turn = repository.save_turn(
        TurnRecord(
            session_id=None,
            player_input="Exploro la mina.",
            narrative="La oscuridad de la mina parece observarte.",
            operation_count=1,
            successful_operation_count=1,
            failed_operation_count=0,
            all_operations_succeeded=True,
            world_changed=True,
        )
    )

    assert turn.id is not None
    assert turn.player_input == (
        "Exploro la mina."
    )
    assert turn.narrative == (
        "La oscuridad de la mina parece observarte."
    )
    assert turn.operation_count == 1
    assert turn.world_changed is True


def test_get_missing_turn_returns_none(
    isolated_database,
):
    repository = TurnRepository()

    assert repository.get_turn(999999) is None


def test_list_turns_returns_saved_turns(
    isolated_database,
):
    repository = TurnRepository()

    repository.save_turn(
        TurnRecord(
            player_input="Primera acción",
            narrative="Primera respuesta",
        )
    )

    repository.save_turn(
        TurnRecord(
            player_input="Segunda acción",
            narrative="Segunda respuesta",
        )
    )

    turns = repository.list_turns()

    assert len(turns) == 2
    assert turns[0].player_input == (
        "Primera acción"
    )
    assert turns[1].player_input == (
        "Segunda acción"
    )


def test_list_turns_filters_by_session(
    isolated_database,
):
    from repositories.campaign_repository import CampaignRepository

    repository = TurnRepository()
    campaign_repository = CampaignRepository()

    session_one = campaign_repository.create_session(
        number=1,
        title="Session One",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    session_two = campaign_repository.create_session(
        number=2,
        title="Session Two",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_one["id"],
            player_input="Sesión uno",
            narrative="Respuesta uno",
        )
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_two["id"],
            player_input="Sesión dos",
            narrative="Respuesta dos",
        )
    )

    turns = repository.list_turns(
        session_id=session_one["id"],
    )

    assert len(turns) == 1
    assert turns[0].session_id == session_one["id"]
    assert turns[0].player_input == (
        "Sesión uno"
    )

def test_list_recent_turns_returns_latest_turns_in_chronological_order(
    isolated_database,
):
    repository = TurnRepository()

    for index in range(1, 6):
        repository.save_turn(
            TurnRecord(
                player_input=f"Acción {index}",
                narrative=f"Narrativa {index}",
            )
        )

    turns = repository.list_recent_turns(
        limit=3,
    )

    assert len(turns) == 3

    assert [
        turn.player_input
        for turn in turns
    ] == [
        "Acción 3",
        "Acción 4",
        "Acción 5",
    ]


def test_list_recent_turns_filters_by_session(
    isolated_database,
):
    from repositories.campaign_repository import CampaignRepository

    repository = TurnRepository()
    campaign_repository = CampaignRepository()

    session_one = campaign_repository.create_session(
        number=1,
        title="Session One",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    session_two = campaign_repository.create_session(
        number=2,
        title="Session Two",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_one["id"],
            player_input="Uno",
            narrative="Narrativa uno",
        )
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_two["id"],
            player_input="Dos",
            narrative="Narrativa dos",
        )
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_one["id"],
            player_input="Tres",
            narrative="Narrativa tres",
        )
    )

    turns = repository.list_recent_turns(
        session_id=session_one["id"],
        limit=10,
    )

    assert [
        turn.player_input
        for turn in turns
    ] == [
        "Uno",
        "Tres",
    ]


def test_list_recent_turns_rejects_invalid_limit(
    isolated_database,
):
    repository = TurnRepository()

    try:
        repository.list_recent_turns(
            limit=0,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_list_recent_turns_rejects_limit_above_maximum(
    isolated_database,
):
    repository = TurnRepository()

    try:
        repository.list_recent_turns(
            limit=101,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_list_recent_turns_rejects_non_integer_limit(
    isolated_database,
):
    repository = TurnRepository()

    try:
        repository.list_recent_turns(
            limit="10",
        )
    except TypeError:
        pass
    else:
        raise AssertionError(
            "Expected TypeError"
        )

def test_list_turns_with_session_id_returns_failed_operation_count(
    isolated_database,
):
    from database import execute, one
    from models.turn_record import TurnRecord
    from repositories.turn_repository import TurnRepository

    execute(
        """
        INSERT INTO sessions (
            number,
            title
        )
        VALUES (?, ?)
        """,
        (999, "test-session"),
    )

    session = one(
        """
        SELECT id
        FROM sessions
        WHERE number=?
        """,
        (999,),
    )

    assert session is not None

    repository = TurnRepository()

    turn = TurnRecord(
        session_id=session["id"],
        player_input="attack",
        narrative="The goblin attacks.",
        operation_count=2,
        successful_operation_count=1,
        failed_operation_count=1,
        all_operations_succeeded=False,
        world_changed=False,
    )

    saved = repository.save_turn(turn)

    assert saved.id is not None

    turns = repository.list_turns(
        session_id=session["id"],
    )

    assert len(turns) == 1
    assert turns[0].failed_operation_count == 1

def test_save_turn_can_use_existing_connection():
    from database import get_conn
    from models.turn_record import TurnRecord
    from repositories.turn_repository import TurnRepository

    repository = TurnRepository()

    turn = TurnRecord(
        session_id=None,
        player_input="attack",
        narrative="The goblin raises its blade.",
        operation_count=1,
        successful_operation_count=1,
        failed_operation_count=0,
        all_operations_succeeded=True,
        world_changed=True,
    )

    with get_conn() as conn:
        saved = repository.save_turn(
            turn,
            conn=conn,
        )

        assert saved.id is not None
        assert saved.player_input == "attack"
        assert saved.operation_count == 1
        assert saved.successful_operation_count == 1
        assert saved.failed_operation_count == 0
        assert saved.all_operations_succeeded is True
        assert saved.world_changed is True

def test_save_turn_with_existing_connection_does_not_commit_independently():
    from database import get_conn
    from models.turn_record import TurnRecord
    from repositories.turn_repository import TurnRepository

    repository = TurnRepository()

    turn = TurnRecord(
        session_id=None,
        player_input="test transaction",
        narrative="Transaction test.",
        operation_count=0,
        successful_operation_count=0,
        failed_operation_count=0,
        all_operations_succeeded=True,
        world_changed=False,
    )

    with get_conn() as conn:
        repository.save_turn(
            turn,
            conn=conn,
        )

        row = conn.execute(
            """
            SELECT
                player_input
            FROM turns
            WHERE player_input=?
            ORDER BY id DESC
            LIMIT 1
            """,
            ("test transaction",),
        ).fetchone()

        assert row is not None

        conn.rollback()

    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                player_input
            FROM turns
            WHERE player_input=?
            ORDER BY id DESC
            LIMIT 1
            """,
            ("test transaction",),
        ).fetchone()

        assert row is None

def test_list_turns_by_session_returns_complete_turn_record(
    isolated_database,
):
    repository = TurnRepository()
    campaign_repository = CampaignRepository()

    session = campaign_repository.create_session(
        number=9001,
        title="Test Session",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    session_id = session["id"]

    saved = repository.save_turn(
        TurnRecord(
            session_id=session_id,
            player_input="Pregunto por Aldric.",
            narrative="El tabernero señala una mesa.",
            operation_count=2,
            successful_operation_count=2,
            failed_operation_count=0,
            all_operations_succeeded=True,
            world_changed=True,
        )
    )

    result = repository.list_turns(
        session_id=session_id,
    )

    assert len(result) == 1

    turn = result[0]

    assert turn.id == saved.id
    assert turn.session_id == session_id
    assert turn.player_input == "Pregunto por Aldric."
    assert turn.narrative == "El tabernero señala una mesa."

    assert turn.operation_count == 2
    assert turn.successful_operation_count == 2
    assert turn.failed_operation_count == 0

    assert turn.all_operations_succeeded is True
    assert turn.world_changed is True


def test_list_turns_by_session_does_not_return_other_sessions(
    isolated_database,
):
    repository = TurnRepository()
    campaign_repository = CampaignRepository()

    session_one = campaign_repository.create_session(
        number=9002,
        title="Session One",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    session_two = campaign_repository.create_session(
        number=9003,
        title="Session Two",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_one["id"],
            player_input="Turno sesión uno.",
            narrative="Narrativa uno.",
        )
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_two["id"],
            player_input="Turno sesión dos.",
            narrative="Narrativa dos.",
        )
    )

    result = repository.list_turns(
        session_id=session_one["id"],
    )

    assert len(result) == 1

    assert result[0].session_id == session_one["id"]
    assert result[0].player_input == (
        "Turno sesión uno."
    )


def test_list_recent_turns_by_session_preserves_complete_metadata(
    isolated_database,
):
    repository = TurnRepository()
    campaign_repository = CampaignRepository()

    session = campaign_repository.create_session(
        number=9004,
        title="Test Session",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    session_id = session["id"]

    repository.save_turn(
        TurnRecord(
            session_id=session_id,
            player_input="Primer turno.",
            narrative="Primera escena.",
            operation_count=3,
            successful_operation_count=3,
            failed_operation_count=0,
            all_operations_succeeded=True,
            world_changed=True,
        )
    )

    repository.save_turn(
        TurnRecord(
            session_id=session_id,
            player_input="Segundo turno.",
            narrative="Segunda escena.",
            operation_count=1,
            successful_operation_count=0,
            failed_operation_count=1,
            all_operations_succeeded=False,
            world_changed=False,
        )
    )

    result = repository.list_recent_turns(
        session_id=session_id,
        limit=2,
    )

    assert len(result) == 2

    first = result[0]
    second = result[1]

    assert first.player_input == "Primer turno."
    assert first.operation_count == 3
    assert first.successful_operation_count == 3
    assert first.failed_operation_count == 0
    assert first.all_operations_succeeded is True
    assert first.world_changed is True

    assert second.player_input == "Segundo turno."
    assert second.operation_count == 1
    assert second.successful_operation_count == 0
    assert second.failed_operation_count == 1
    assert second.all_operations_succeeded is False
    assert second.world_changed is False


def test_list_turns_returns_turns_in_ascending_order(
    isolated_database,
):
    repository = TurnRepository()
    campaign_repository = CampaignRepository()

    session = campaign_repository.create_session(
        number=9005,
        title="Test Session",
        summary="",
        start_location="",
        end_location="",
        notes="",
    )

    session_id = session["id"]

    first = repository.save_turn(
        TurnRecord(
            session_id=session_id,
            player_input="Primero.",
            narrative="Primero.",
        )
    )

    second = repository.save_turn(
        TurnRecord(
            session_id=session_id,
            player_input="Segundo.",
            narrative="Segundo.",
        )
    )

    result = repository.list_turns(
        session_id=session_id,
    )

    assert [turn.id for turn in result] == [
        first.id,
        second.id,
    ]