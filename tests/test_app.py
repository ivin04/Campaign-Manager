import pytest

from app import create_campaign_turn_service
from repositories.campaign_repository import CampaignRepository
from repositories.character_repository import CharacterRepository
from repositories.entity_repository import EntityRepository
from services.campaign_state_service import CampaignStateService
from services.context_builder import ContextBuilder
from services.memory_search_service import MemorySearchService
from services.world_service import WorldService


def test_create_campaign_turn_service_uses_provided_context_builder():
    world_service = WorldService()

    memory_search_service = MemorySearchService()

    context_builder = ContextBuilder(
        memory_search_service=memory_search_service,
    )

    campaign_repository = CampaignRepository()

    character_repository = CharacterRepository()

    campaign_state_service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=character_repository,
        world_service=world_service,
        entity_repository=EntityRepository(),
    )

    service = create_campaign_turn_service(
        world_service=world_service,
        context_builder=context_builder,
        campaign_state_service=campaign_state_service,
    )

    assert service.turn_resolution_service is not None
    assert service.campaign_state_service is campaign_state_service

    dm_service = service.turn_resolution_service.dm_service

    assert dm_service.context_builder is context_builder


def test_create_campaign_turn_service_rejects_invalid_context_builder():
    world_service = WorldService()

    campaign_repository = CampaignRepository()

    character_repository = CharacterRepository()

    campaign_state_service = CampaignStateService(
        campaign_repository=campaign_repository,
        character_repository=character_repository,
        world_service=world_service,
        entity_repository=EntityRepository(),
    )

    with pytest.raises(
        TypeError,
        match="context_builder must be a ContextBuilder",
    ):
        create_campaign_turn_service(
            world_service=world_service,
            context_builder="invalid",
            campaign_state_service=campaign_state_service,
        )

def test_get_turns_accepts_limit(client):
    response = client.get(
        "/turns?limit=5"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)
    assert len(data) <= 5


def test_get_turns_rejects_invalid_limit(client):
    response = client.get(
        "/turns?limit=0"
    )

    assert response.status_code == 422


def test_get_turns_rejects_limit_above_maximum(client):
    response = client.get(
        "/turns?limit=101"
    )

    assert response.status_code == 422


def test_get_turns_filters_by_session_and_limit(
    client,
    monkeypatch,
):
    calls = []

    def fake_list_turns(
        *,
        session_id=None,
        limit=None,
    ):
        calls.append(
            {
                "session_id": session_id,
                "limit": limit,
            }
        )

        return []

    monkeypatch.setattr(
        "app.turn_repository.list_turns",
        fake_list_turns,
    )

    response = client.get(
        "/turns?session_id=7&limit=5"
    )

    assert response.status_code == 200
    assert response.json() == []

    assert calls == [
        {
            "session_id": 7,
            "limit": 5,
        }
    ]


def test_get_turns_uses_default_limit(
    client,
    monkeypatch,
):
    calls = []

    def fake_list_turns(
        *,
        session_id=None,
        limit=None,
    ):
        calls.append(
            {
                "session_id": session_id,
                "limit": limit,
            }
        )

        return []

    monkeypatch.setattr(
        "app.turn_repository.list_turns",
        fake_list_turns,
    )

    response = client.get(
        "/turns"
    )

    assert response.status_code == 200

    assert calls == [
        {
            "session_id": None,
            "limit": 50,
        }
    ]