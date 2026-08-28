import pytest

from app import create_campaign_turn_service
from models.world_state import WorldState
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