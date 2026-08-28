from models.turn_record import TurnRecord
from repositories.turn_repository import TurnRepository


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
    turn_repository,
):
    turn = TurnRecord(
        session_id=42,
        player_input="attack",
        narrative="The goblin attacks.",
        operation_count=2,
        successful_operation_count=1,
        failed_operation_count=1,
        all_operations_succeeded=False,
        world_changed=False,
    )

    saved = turn_repository.save_turn(turn)

    assert saved.failed_operation_count == 1

    turns = turn_repository.list_turns(
        session_id=42,
    )

    assert len(turns) == 1

    assert turns[0].failed_operation_count == 1