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