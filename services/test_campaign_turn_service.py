import pytest

from models.turn_resolution_result import (
    TurnResolutionResult,
)
from models.world_state import WorldState

from services.campaign_turn_service import (
    CampaignTurnService,
    CampaignTurnServiceError,
)
from services.turn_resolution_service import (
    TurnResolutionService,
)
from services.world_service import WorldService


# ============================================================
# FAKES
# ============================================================


class RecordingTurnResolutionService:

    def __init__(
        self,
        result=None,
        exception=None,
    ):
        self.result = result
        self.exception = exception
        self.calls = []

    def resolve_turn(
        self,
        world,
        player_input,
    ):
        self.calls.append(
            (
                "resolve_turn",
                world,
                player_input,
            )
        )

        if self.exception:
            raise self.exception

        return self.result


class RecordingWorldService:

    def __init__(
        self,
        world=None,
        load_exception=None,
        save_exception=None,
    ):
        self.world = (
            world
            if world is not None
            else WorldState()
        )

        self.load_exception = load_exception
        self.save_exception = save_exception

        self.load_calls = 0
        self.save_calls = 0
        self.get_world_calls = 0

    def load(self):
        self.load_calls += 1

        if self.load_exception:
            raise self.load_exception

        return self.world

    def save(self):
        self.save_calls += 1

        if self.save_exception:
            raise self.save_exception

    def get_world(self):
        self.get_world_calls += 1

        return self.world


# ============================================================
# HELPERS
# ============================================================


def make_result(
    *,
    player_input="Exploro.",
    narrative="La puerta se abre.",
    operations=(),
    operation_results=(),
):
    return TurnResolutionResult(
        player_input=player_input,
        narrative=narrative,
        operations=operations,
        operation_results=operation_results,
    )


def make_service(
    *,
    result=None,
    turn_exception=None,
    world=None,
    load_exception=None,
    save_exception=None,
):
    world_service = RecordingWorldService(
        world=world,
        load_exception=load_exception,
        save_exception=save_exception,
    )

    turn_service = RecordingTurnResolutionService(
        result=result,
        exception=turn_exception,
    )

    service = CampaignTurnService(
        turn_resolution_service=turn_service,
        world_service=world_service,
    )

    return (
        service,
        turn_service,
        world_service,
    )


# ============================================================
# CONSTRUCTOR
# ============================================================


def test_constructor_requires_turn_resolution_service():

    with pytest.raises(TypeError):

        CampaignTurnService(
            turn_resolution_service=object(),
            world_service=WorldService(),
        )


def test_constructor_requires_world_service():

    with pytest.raises(TypeError):

        CampaignTurnService(
            turn_resolution_service=object(),
            world_service=object(),
        )


# ============================================================
# INPUT VALIDATION
# ============================================================


def test_player_input_must_be_string():

    result = make_result()

    service, *_ = make_service(
        result=result,
    )

    with pytest.raises(TypeError):

        service.play_turn(
            123,
        )


def test_empty_player_input_is_rejected():

    result = make_result()

    service, *_ = make_service(
        result=result,
    )

    with pytest.raises(
        CampaignTurnServiceError,
    ):

        service.play_turn(
            "   ",
        )


def test_player_input_is_stripped_before_resolution():

    result = make_result()

    service, turn_service, _ = (
        make_service(
            result=result,
        )
    )

    service.play_turn(
        "   Exploro.   ",
    )

    assert (
        turn_service.calls[0][2]
        == "Exploro."
    )


# ============================================================
# TURN RESOLUTION
# ============================================================


def test_current_world_is_passed_to_turn_resolution():

    world = WorldState()

    result = make_result()

    service, turn_service, world_service = (
        make_service(
            result=result,
            world=world,
        )
    )

    service.play_turn(
        "Exploro.",
    )

    assert turn_service.calls == [
        (
            "resolve_turn",
            world,
            "Exploro.",
        )
    ]

    assert world_service.get_world_calls == 1


def test_resolution_result_is_preserved():

    result = make_result(
        player_input="Exploro.",
        narrative="Una figura aparece.",
    )

    service, *_ = make_service(
        result=result,
    )

    returned = service.play_turn(
        "Exploro.",
    )

    assert returned is result


def test_invalid_resolution_result_is_rejected():

    service, *_ = make_service(
        result="not a result",
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="invalid TurnResolutionResult",
    ):

        service.play_turn(
            "Exploro.",
        )


# ============================================================
# PERSISTENCE
# ============================================================


def test_world_is_saved_when_world_changed():

    result = make_result()

    # Simulamos un turno que produjo una operación exitosa.
    from models.operation_result import OperationResult

    operation_result = OperationResult(
        success=True,
    )

    result = make_result(
        operation_results=(
            operation_result,
        ),
    )

    service, _, world_service = (
        make_service(
            result=result,
        )
    )

    service.play_turn(
        "Conozco a Aldric.",
    )

    assert world_service.save_calls == 1


def test_world_is_not_saved_when_nothing_changed():

    result = make_result(
        operations=(),
        operation_results=(),
    )

    service, _, world_service = (
        make_service(
            result=result,
        )
    )

    service.play_turn(
        "Miro alrededor.",
    )

    assert world_service.save_calls == 0


# ============================================================
# ERROR HANDLING
# ============================================================


def test_turn_resolution_failure_is_wrapped():

    service, _, _ = make_service(
        turn_exception=RuntimeError(
            "boom"
        ),
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="turn resolution failed",
    ):

        service.play_turn(
            "Exploro.",
        )


def test_save_failure_is_wrapped():

    from models.operation_result import OperationResult

    result = make_result(
        operation_results=(
            OperationResult(
                success=True,
            ),
        ),
    )

    service, _, _ = make_service(
        result=result,
        save_exception=RuntimeError(
            "database failed"
        ),
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to persist campaign world",
    ):

        service.play_turn(
            "Exploro.",
        )


# ============================================================
# LOAD / SAVE
# ============================================================


def test_load_delegates_to_world_service():

    world = WorldState()

    service, _, world_service = (
        make_service(
            world=world,
        )
    )

    returned = service.load()

    assert returned is world
    assert world_service.load_calls == 1


def test_load_failure_is_wrapped():

    service, _, _ = make_service(
        load_exception=RuntimeError(
            "database failed"
        ),
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to load campaign world",
    ):

        service.load()


def test_save_delegates_to_world_service():

    service, _, world_service = (
        make_service()
    )

    service.save()

    assert world_service.save_calls == 1


def test_save_failure_is_wrapped():

    service, _, _ = make_service(
        save_exception=RuntimeError(
            "database failed"
        ),
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to save campaign world",
    ):

        service.save()


# ============================================================
# ALIASES
# ============================================================


def test_run_turn_is_alias_for_play_turn():

    result = make_result()

    service, turn_service, _ = (
        make_service(
            result=result,
        )
    )

    returned = service.run_turn(
        "Exploro.",
    )

    assert returned is result

    assert turn_service.calls


def test_resolve_turn_is_alias_for_play_turn():

    result = make_result()

    service, turn_service, _ = (
        make_service(
            result=result,
        )
    )

    returned = service.resolve_turn(
        "Exploro.",
    )

    assert returned is result

    assert turn_service.calls


def test_service_is_callable():

    result = make_result()

    service, turn_service, _ = (
        make_service(
            result=result,
        )
    )

    returned = service(
        "Exploro.",
    )

    assert returned is result

    assert turn_service.calls


# ============================================================
# WORLD ACCESS
# ============================================================


def test_get_world_delegates_to_world_service():

    world = WorldState()

    service, _, world_service = (
        make_service(
            world=world,
        )
    )

    returned = service.get_world()

    assert returned is world
    assert world_service.get_world_calls == 1