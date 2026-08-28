from models.campaign_state import CampaignState


def test_campaign_state_has_expected_defaults():
    state = CampaignState()

    assert state.campaign_id == 1
    assert state.name == ""
    assert state.system == "D&D 5e 2014"
    assert state.tone == ""
    assert state.current_location_id is None
    assert state.current_session_id is None
    assert state.active_character_id is None
    assert state.summary == ""


def test_campaign_state_can_store_campaign_context():
    state = CampaignState(
        campaign_id=1,
        name="Vorder's Hold",
        system="D&D 5e 2014",
        tone="dark",
        current_location_id=12,
        current_session_id=4,
        active_character_id=7,
        summary="Fungoso ha llegado a Vorder's Hold.",
    )

    assert state.name == "Vorder's Hold"
    assert state.current_location_id == 12
    assert state.current_session_id == 4
    assert state.active_character_id == 7
    assert state.summary == (
        "Fungoso ha llegado a Vorder's Hold."
    )