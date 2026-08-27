import pytest

from app import create_campaign_turn_service, create_context_builder
from services.world_service import WorldService
from services.memory_search_service import MemorySearchService
from services.context_builder import ContextBuilder

def test_create_campaign_turn_service_uses_provided_context_builder():
    world_service = WorldService()

    memory_search_service = MemorySearchService()

    context_builder = ContextBuilder(
        memory_search_service=memory_search_service,
    )

    service = create_campaign_turn_service(
        world_service=world_service,
        context_builder=context_builder,
    )

    dm_service = (
        service.turn_resolution_service.dm_service
    )

    assert dm_service.context_builder is context_builder

def test_create_campaign_turn_service_rejects_invalid_context_builder():
    with pytest.raises(
        TypeError,
        match="context_builder must be a ContextBuilder",
    ):
        create_campaign_turn_service(
            world_service=WorldService(),
            context_builder=object(),
        )

def test_create_context_builder_rejects_invalid_memory_search_service():
    with pytest.raises(
        TypeError,
        match=(
            "memory_search_service must be "
            "a MemorySearchService"
        ),
    ):
        create_context_builder(
            memory_search_service=object(),
        )