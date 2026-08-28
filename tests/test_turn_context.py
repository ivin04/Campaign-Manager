import pytest

from models.campaign_state import CampaignState
from models.character_state import CharacterState
from models.session_state import SessionState
from models.turn_context import TurnContext
from models.world_state import WorldState


def make_context():
    return TurnContext(
        campaign=CampaignState(),
        current_session=None,
        active_character=None,
        world=WorldState(),
    )


def test_turn_context_accepts_valid_state_objects():
    context = make_context()

    assert isinstance(
        context.campaign,
        CampaignState,
    )

    assert context.current_session is None
    assert context.active_character is None

    assert isinstance(
        context.world,
        WorldState,
    )


def test_turn_context_rejects_invalid_campaign():
    with pytest.raises(
        TypeError,
        match="campaign must be a CampaignState",
    ):
        TurnContext(
            campaign={},
            current_session=None,
            active_character=None,
            world=WorldState(),
        )


def test_turn_context_rejects_invalid_session():
    with pytest.raises(
        TypeError,
        match="current_session must be a SessionState or None",
    ):
        TurnContext(
            campaign=CampaignState(),
            current_session={},
            active_character=None,
            world=WorldState(),
        )


def test_turn_context_rejects_invalid_character():
    with pytest.raises(
        TypeError,
        match="active_character must be a CharacterState or None",
    ):
        TurnContext(
            campaign=CampaignState(),
            current_session=None,
            active_character={},
            world=WorldState(),
        )


def test_turn_context_rejects_invalid_world():
    with pytest.raises(
        TypeError,
        match="world must be a WorldState",
    ):
        TurnContext(
            campaign=CampaignState(),
            current_session=None,
            active_character=None,
            world={},
        )


def test_turn_context_accepts_session_and_character():
    session = SessionState(
        session_id=1,
        number=1,
        title="Opening",
    )

    character = CharacterState(
        entity_id=10,
    )

    context = TurnContext(
        campaign=CampaignState(
            campaign_id=1,
            name="Test Campaign",
        ),
        current_session=session,
        active_character=character,
        world=WorldState(),
    )

    assert context.current_session is session
    assert context.active_character is character