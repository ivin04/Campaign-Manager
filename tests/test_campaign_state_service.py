from models.world_state import WorldState

from repositories.campaign_repository import CampaignRepository
from repositories.character_repository import CharacterRepository

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

    assert state.campaign is not None
    assert state.current_session is None
    assert state.active_character is None
    assert isinstance(
        state.world,
        WorldState,
    )


def test_campaign_state_service_sets_and_gets_current_session(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(campaign_repository)

    session = campaign_repository.create_session(
        number=1001,
        title="Opening",
        summary="Inicio.",
        start_location="Vorder's Hold",
        end_location="La mina",
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

    assert state.current_session is not None
    assert state.current_session["id"] == session["id"]


def test_campaign_state_service_can_clear_current_session(
    isolated_database,
):
    campaign_repository = CampaignRepository()

    create_campaign(campaign_repository)

    session = campaign_repository.create_session(
        number=1002,
        title="Opening",
        summary="Inicio.",
        start_location="Vorder's Hold",
        end_location="La mina",
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

    assert state.current_session is None


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