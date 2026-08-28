from operations.world_operations import CreateEntityOperation
import pytest

from models.turn_resolution_result import (
    TurnResolutionResult,
)
from models.turn_context import TurnContext
from models.turn_record import TurnRecord
from models.world_state import WorldState

from services.campaign_turn_service import (
    CampaignTurnService,
    CampaignTurnServiceError,
)
from services.turn_resolution_service import (
    TurnResolutionService,
    TurnResolutionServiceError,
)
from services.world_service import WorldService
from models.operation_result import OperationResult, OperationStatus
from repositories.turn_repository import TurnRepository

from services.campaign_state_service import (
    CampaignState,
    CampaignStateService,
    CampaignStateServiceError,
)


# ============================================================
# FAKES
# ============================================================


class RecordingWorldService(WorldService):

    def __init__(self):
        super().__init__()

        self.world = WorldState()

        self.get_world_calls = 0
        self.save_calls = 0
        self.load_calls = 0

        self.save_error = None
        self.load_error = None

    def get_world(self):
        self.get_world_calls += 1

        return self.world

    def save(self):
        self.save_calls += 1

        if self.save_error is not None:
            raise self.save_error

    def load(self):
        self.load_calls += 1

        if self.load_error is not None:
            raise self.load_error

        return self.world

class RecordingCampaignStateService(
    CampaignStateService
):

    def __init__(
        self,
        world_service,
    ):
        self.world_service = world_service

        self.get_state_calls = 0
        self.get_turn_context_calls = 0
        self.get_world_calls = 0
        self.load_world_calls = 0
        self.save_world_calls = 0

        self.state_error = None
        self.world_error = None
        self.load_error = None
        self.save_error = None

    def get_state(self):
        self.get_state_calls += 1

        if self.state_error is not None:
            raise self.state_error

        return CampaignState(
            campaign=CampaignState(),
            current_session=None,
            active_character=None,
            world=self.world_service.world,
        )

    def get_turn_context(self):
        self.get_turn_context_calls += 1

        if self.state_error is not None:
            raise self.state_error

        return TurnContext(
            campaign=CampaignState(),
            current_session=None,
            active_character=None,
            world=self.world_service.world,
        )

    def get_world(self):
        self.get_world_calls += 1

        if self.world_error is not None:
            raise self.world_error

        return self.world_service.world

    def load_world(self):
        self.load_world_calls += 1

        if self.load_error is not None:
            raise self.load_error

        return self.world_service.world

    def save_world(self):
        self.save_world_calls += 1

        if self.save_error is not None:
            raise self.save_error


class RecordingTurnResolutionService(
    TurnResolutionService
):

    def __init__(
        self,
        result,
    ):
        self.result = result

        self.calls = []

        self.error = None

    def resolve_turn(
        self,
        world,
        player_input,
    ):
        self.calls.append(
            (
                world,
                player_input,
            )
        )

        if self.error is not None:
            raise self.error

        return self.result


# ============================================================
# HELPERS
# ============================================================


def make_result(
    *,
    player_input="Exploro.",
    narrative="No ocurre nada.",
    world_changed=False,
):
    """
    Construye un TurnResolutionResult para los tests.

    world_changed no se pasa al constructor porque es una
    propiedad derivada de operation_results.
    """

    operations = ()
    operation_results = ()

    if world_changed:
        operation = CreateEntityOperation(
            name="TestEntity",
            entity_type="test",
            description="Test entity.",
            notes="",
            active=True,
        )

        operations = (operation,)

        # No podemos inventar un OperationResult aquí sin conocer
        # su constructor real. Para estos tests concretos,
        # el resultado debe representar una operación exitosa.
        operation_results = (
            OperationResult(
                status=OperationStatus.SUCCESS,
                operation=operation,
            ),
        )

    return TurnResolutionResult(
        player_input=player_input,
        narrative=narrative,
        operations=operations,
        operation_results=operation_results,
    )


def make_service(
    *,
    result=None,
    world_service=None,
    campaign_state_service=None,
):
    if result is None:
        result = make_result()

    if world_service is None:
        world_service = RecordingWorldService()

    turn_resolution_service = (
        RecordingTurnResolutionService(
            result
        )
    )

    service = CampaignTurnService(
        turn_resolution_service=(
            turn_resolution_service
        ),
        world_service=world_service,
        campaign_state_service=(
            campaign_state_service
        ),
    )

    return (
        service,
        turn_resolution_service,
        world_service,
        campaign_state_service,
    )


# ============================================================
# CONSTRUCTOR
# ============================================================


def test_constructor_requires_turn_resolution_service():

    world_service = RecordingWorldService()

    with pytest.raises(TypeError):

        CampaignTurnService(
            turn_resolution_service=object(),
            world_service=world_service,
        )


def test_constructor_requires_world_service():

    result = make_result()

    turn_resolution_service = (
        RecordingTurnResolutionService(
            result
        )
    )

    with pytest.raises(TypeError):

        CampaignTurnService(
            turn_resolution_service=(
                turn_resolution_service
            ),
            world_service=object(),
        )


# ============================================================
# INPUT VALIDATION
# ============================================================


def test_player_input_must_be_string():

    service, _, _, _ = make_service()

    with pytest.raises(TypeError):

        service.play_turn(123)


def test_empty_player_input_is_rejected():

    service, _, _, _ = make_service()

    with pytest.raises(
        CampaignTurnServiceError
    ):

        service.play_turn("   ")


def test_player_input_is_stripped():

    result = make_result(
        player_input="Exploro."
    )

    service, resolver, _, _ = make_service(
        result=result
    )

    returned = service.play_turn(
        "   Exploro.   "
    )

    assert returned is result
    assert len(resolver.calls) == 1
    assert resolver.calls[0][1] == "Exploro."


# ============================================================
# WORLD
# ============================================================


def test_get_world_is_called_before_resolution():

    result = make_result()

    service, resolver, world_service, campaign_state_service = (
        make_service(
                result=result
            )
        )

    service.play_turn(
        "Exploro."
    )

    assert (
        world_service.get_world_calls
        == 1
    )

    assert len(
        resolver.calls
    ) == 1

    assert isinstance(
        resolver.calls[0][0],
        TurnContext,
    )

    assert (
        resolver.calls[0][0].world
        is world_service.world
    )


def test_invalid_world_returned_by_world_service_is_rejected():

    result = make_result()

    world_service = RecordingWorldService()

    world_service.world = object()

    service, resolver, _, _ = make_service(
        result=result,
        world_service=world_service,
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="invalid WorldState",
    ):

        service.play_turn(
            "Exploro."
        )

    assert resolver.calls == []


# ============================================================
# RESOLUTION
# ============================================================


def test_resolution_result_is_preserved():

    result = make_result(
        player_input="Abro.",
        narrative="La puerta se abre.",
        world_changed=False,
    )

    service, _, _, _ = make_service(
        result=result
    )

    returned = service.play_turn(
        "Abro."
    )

    assert returned is result

    assert (
        returned.narrative
        == "La puerta se abre."
    )

    assert (
        returned.player_input
        == "Abro."
    )


def test_turn_resolution_service_error_is_wrapped():

    result = make_result()

    service, resolver, _, _ = make_service(
        result=result
    )

    resolver.error = (
        TurnResolutionServiceError(
            "DM failed"
        )
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="turn resolution failed",
    ) as exc_info:

        service.play_turn(
            "Exploro."
        )

    assert isinstance(
        exc_info.value.__cause__,
        TurnResolutionServiceError,
    )


def test_unexpected_resolution_error_is_wrapped():

    result = make_result()

    service, resolver, _, _ = make_service(
        result=result
    )

    resolver.error = RuntimeError(
        "unexpected"
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="unexpected error while resolving turn",
    ) as exc_info:

        service.play_turn(
            "Exploro."
        )

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )


def test_invalid_resolution_result_is_rejected():

    service, resolver, _, _ = make_service(
        result=object()
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="invalid TurnResolutionResult",
    ):

        service.play_turn(
            "Exploro."
        )


# ============================================================
# PERSISTENCE
# ============================================================


def test_world_is_not_saved_when_world_did_not_change():

    result = make_result(
        world_changed=False
    )

    service, _, world_service, _  = (
        make_service(
            result=result
        )
    )

    service.play_turn(
        "Miro alrededor."
    )

    assert (
        world_service.save_calls
        == 0
    )


def test_play_turn_does_not_save_world_directly():

    result = make_result(
        world_changed=True
    )

    service, _, world_service, _  = (
        make_service(
            result=result
        )
    )

    service.play_turn(
        "Creo una entidad."
    )

    assert (
        world_service.save_calls
        == 0
    )


def test_save_failure_is_wrapped():

    result = make_result(
        world_changed=True
    )

    world_service = RecordingWorldService()

    world_service.save_error = RuntimeError(
        "database unavailable"
    )

    service, _, _, _ = make_service(
        result=result,
        world_service=world_service,
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to persist campaign world",
    ) as exc_info:

        service.play_turn(
            "Creo una entidad."
        )

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )


# ============================================================
# LOAD
# ============================================================


def test_load_returns_world():

    service, _, world_service, _  = (
        make_service()
    )

    returned = service.load()

    assert returned is (
        world_service.world
    )

    assert (
        world_service.load_calls
        == 1
    )


def test_load_failure_is_wrapped():

    service, _, world_service, _  = (
        make_service()
    )

    world_service.load_error = RuntimeError(
        "database unavailable"
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to load campaign world",
    ) as exc_info:

        service.load()

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )


def test_load_rejects_invalid_world():

    service, _, world_service, _  = (
        make_service()
    )

    world_service.world = object()

    with pytest.raises(
        CampaignTurnServiceError,
        match="invalid WorldState",
    ):

        service.load()


# ============================================================
# EXPLICIT SAVE
# ============================================================


def test_save_delegates_to_world_service():

    service, _, world_service, _  = (
        make_service()
    )

    service.save()

    assert (
        world_service.save_calls
        == 1
    )


def test_save_failure_is_wrapped():

    service, _, world_service, _  = (
        make_service()
    )

    world_service.save_error = RuntimeError(
        "database unavailable"
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to save campaign world",
    ) as exc_info:

        service.save()

    assert isinstance(
        exc_info.value.__cause__,
        RuntimeError,
    )


# ============================================================
# GET WORLD
# ============================================================


def test_get_world_returns_current_world():

    service, _, world_service, _  = (
        make_service()
    )

    returned = service.get_world()

    assert returned is (
        world_service.world
    )

    assert (
        world_service.get_world_calls
        == 1
    )


def test_get_world_rejects_invalid_world():

    service, _, world_service, _  = (
        make_service()
    )

    world_service.world = object()

    with pytest.raises(
        CampaignTurnServiceError,
        match="invalid WorldState",
    ):

        service.get_world()

# ============================================================
# CAMPAIGN STATE INTEGRATION
# ============================================================


def test_play_turn_uses_campaign_state_service():
    result = make_result()

    world_service = RecordingWorldService()

    campaign_state_service = (
        RecordingCampaignStateService(
            world_service
        )
    )

    service, resolver, _, state_service = (
        make_service(
            result=result,
            world_service=world_service,
            campaign_state_service=(
                campaign_state_service
            ),
        )
    )

    returned = service.play_turn(
        "Exploro."
    )

    assert returned is result

    assert (
        state_service.get_turn_context_calls
        == 1
    )

    assert len(
        resolver.calls
    ) == 1

    assert isinstance(
        resolver.calls[0][0],
        TurnContext,
    )

    assert (
        resolver.calls[0][0].world
        is world_service.world
    )


def test_play_turn_does_not_call_world_service_directly():
    result = make_result()

    world_service = RecordingWorldService()

    campaign_state_service = (
        RecordingCampaignStateService(
            world_service
        )
    )

    service, _, _, _ = make_service(
        result=result,
        world_service=world_service,
        campaign_state_service=(
            campaign_state_service
        ),
    )

    service.play_turn(
        "Exploro."
    )

    # CampaignTurnService obtiene el mundo
    # exclusivamente a través de CampaignStateService.
    assert (
        campaign_state_service.get_turn_context_calls
        == 1
    )


def test_campaign_state_service_error_is_wrapped():
    result = make_result()

    world_service = RecordingWorldService()

    campaign_state_service = (
        RecordingCampaignStateService(
            world_service
        )
    )

    campaign_state_service.state_error = (
        CampaignStateServiceError(
            "campaign does not exist"
        )
    )

    service, resolver, _, _ = make_service(
        result=result,
        world_service=world_service,
        campaign_state_service=(
            campaign_state_service
        ),
    )

    with pytest.raises(
        CampaignTurnServiceError,
        match="failed to obtain campaign turn context",
    ) as exc_info:

        service.play_turn(
            "Exploro."
        )

    assert isinstance(
        exc_info.value.__cause__,
        CampaignStateServiceError,
    )

    assert resolver.calls == []


def test_load_delegates_to_campaign_state_service():
    world_service = RecordingWorldService()

    campaign_state_service = (
        RecordingCampaignStateService(
            world_service
        )
    )

    service, _, _, _ = make_service(
        world_service=world_service,
        campaign_state_service=(
            campaign_state_service
        ),
    )

    returned = service.load()

    assert returned is world_service.world

    assert (
        campaign_state_service.load_world_calls
        == 1
    )


def test_save_delegates_to_campaign_state_service():
    world_service = RecordingWorldService()

    campaign_state_service = (
        RecordingCampaignStateService(
            world_service
        )
    )

    service, _, _, _ = make_service(
        world_service=world_service,
        campaign_state_service=(
            campaign_state_service
        ),
    )

    service.save()

    assert (
        campaign_state_service.save_world_calls
        == 1
    )


def test_get_world_delegates_to_campaign_state_service():
    world_service = RecordingWorldService()

    campaign_state_service = (
        RecordingCampaignStateService(
            world_service
        )
    )

    service, _, _, _ = make_service(
        world_service=world_service,
        campaign_state_service=(
            campaign_state_service
        ),
    )

    returned = service.get_world()

    assert (
        returned
        is world_service.world
    )

    assert (
        campaign_state_service.get_turn_context_calls
        == 1
    )

def test_play_turn_loads_recent_turns_before_resolving():

    recent_turns = [
        TurnRecord(
            id=1,
            session_id=10,
            player_input="Entré en la taberna.",
            narrative="El tabernero levantó la mirada.",
        ),
        TurnRecord(
            id=2,
            session_id=10,
            player_input="Pregunté por el camino norte.",
            narrative="El tabernero señaló hacia las montañas.",
        ),
    ]

    class RecordingTurnRepository(TurnRepository):

        def __init__(self):
            self.calls = []

        def list_recent_turns(
            self,
            *,
            session_id=None,
            limit=10,
        ):
            self.calls.append(
                (
                    session_id,
                    limit,
                )
            )

            return recent_turns

        def save_turn(self, turn):
            return turn

    class RecordingTurnResolutionService(
        TurnResolutionService
    ):

        def __init__(self):
            self.recent_turns = None
            self.calls = []

        def resolve_turn(
            self,
            turn_context,
            player_input,
            *,
            recent_turns=None,
        ):
            self.calls.append(
                (
                    turn_context,
                    player_input,
                )
            )

            self.recent_turns = recent_turns

            return make_result(
                player_input=player_input,
            )

    world_service = RecordingWorldService()

    turn_repository = RecordingTurnRepository()

    resolver = RecordingTurnResolutionService()

    service = CampaignTurnService(
        turn_resolution_service=resolver,
        world_service=world_service,
        turn_repository=turn_repository,
    )

    result = service.play_turn(
        "  Pregunto por el camino.  "
    )

    assert result.player_input == (
        "Pregunto por el camino."
    )

    assert resolver.recent_turns == recent_turns

    assert turn_repository.calls == [
        (None, 10),
    ]

    assert len(resolver.calls) == 1

    assert (
        resolver.calls[0][1]
        == "Pregunto por el camino."
    )