from repositories.campaign_repository import CampaignRepository
from repositories.character_repository import CharacterRepository
from models.campaign_state import CampaignState
from models.turn_context import TurnContext
from models.world_state import WorldState

from services.campaign_state_service import (
    CampaignStateService,
    CampaignStateServiceError,
)

from services.world_service import WorldService


def create_campaign(repository):
    from database import execute

    execute(
        """
        INSERT INTO campaign (
            id,
            name,
            system,
            tone,
            summary
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            1,
            "Test Campaign",
            "D&D 5e 2014",
            "",
            "",
        ),
    )


def make_service():
    return CampaignStateService(
        campaign_repository=CampaignRepository(),
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )


def test_campaign_state_service_returns_complete_state(
    isolated_database,
):
    repository = CampaignRepository()

    create_campaign(repository)

    service = CampaignStateService(
        campaign_repository=repository,
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )

    state = service.get_state()

    assert state.campaign_id == 1
    assert state.name == "Test Campaign"
    assert state.system == "D&D 5e 2014"
    assert state.current_session_id is None
    assert state.active_character_id is None


def test_campaign_state_service_sets_and_gets_current_session(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(
        campaign_repository
    )

    session = campaign_repository.create_session(
        number=1,
        title="Session 1",
        summary="First session",
        start_location="Vorder's Hold",
        end_location="",
        notes="",
    )

    service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )

    state = service.set_current_session(
        session_id=session["id"],
    )

    assert isinstance(
        state,
        CampaignState,
    )

    assert state.current_session_id == session["id"]

    state = service.get_state()

    assert isinstance(
        state,
        CampaignState,
    )

    assert state.current_session_id == session["id"]


def test_campaign_state_service_can_clear_current_session(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(
        campaign_repository
    )

    session = campaign_repository.create_session(
        number=1,
        title="Session 1",
        summary="First session",
        start_location="Vorder's Hold",
        end_location="",
        notes="",
    )

    service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )

    service.set_current_session(
        session_id=session["id"],
    )

    state = service.set_current_session(
        session_id=None,
    )

    assert isinstance(
        state,
        CampaignState,
    )

    assert state.current_session_id is None


def test_campaign_state_service_rejects_missing_session(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(campaign_repository)

    service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )

    try:
        service.set_current_session(
            session_id=999999,
        )
    except CampaignStateServiceError:
        pass
    else:
        raise AssertionError(
            "Expected CampaignStateServiceError"
        )


def test_campaign_state_service_rejects_missing_active_character(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(campaign_repository)

    service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )

    try:
        service.set_active_character(
            character_id=999999,
        )
    except CampaignStateServiceError:
        pass
    else:
        raise AssertionError(
            "Expected CampaignStateServiceError"
        )

def test_campaign_state_service_builds_typed_turn_context(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(
        campaign_repository
    )

    service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=CharacterRepository(),
        world_service=WorldService(),
    )

    context = service.get_turn_context()

    assert isinstance(
        context,
        TurnContext,
    )

    assert isinstance(
        context.campaign,
        CampaignState,
    )

    assert context.campaign.name == (
        "Test Campaign"
    )

    assert context.current_session is None
    assert context.active_character is None

    assert isinstance(
        context.world,
        WorldState,
    )