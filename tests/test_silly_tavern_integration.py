import pytest

from models.schemas import (
    SillyTavernContextIn,
    SillyTavernTurnIn,
)


def test_silly_tavern_context_schema_accepts_query():
    data = SillyTavernContextIn(
        query="Entro en la taberna."
    )

    assert data.query == (
        "Entro en la taberna."
    )


def test_silly_tavern_context_schema_strips_query():
    data = SillyTavernContextIn(
        query="  Entro en la taberna.  "
    )

    assert data.query == (
        "Entro en la taberna."
    )


def test_silly_tavern_context_schema_rejects_empty_query():
    with pytest.raises(ValueError):
        SillyTavernContextIn(
            query="   "
        )


def test_silly_tavern_turn_schema_accepts_valid_data():
    data = SillyTavernTurnIn(
        player_input="Abro la puerta.",
        narrative=(
            "La puerta se abre con un chirrido "
            "lento y desagradable."
        ),
    )

    assert data.player_input == (
        "Abro la puerta."
    )

    assert data.narrative == (
        "La puerta se abre con un chirrido "
        "lento y desagradable."
    )


def test_silly_tavern_turn_schema_strips_text():
    data = SillyTavernTurnIn(
        player_input="  Abro la puerta.  ",
        narrative="  La puerta se abre.  ",
    )

    assert data.player_input == (
        "Abro la puerta."
    )

    assert data.narrative == (
        "La puerta se abre."
    )


def test_silly_tavern_turn_schema_rejects_empty_player_input():
    with pytest.raises(ValueError):
        SillyTavernTurnIn(
            player_input="   ",
            narrative="Narrativa.",
        )


def test_silly_tavern_turn_schema_rejects_empty_narrative():
    with pytest.raises(ValueError):
        SillyTavernTurnIn(
            player_input="Abro la puerta.",
            narrative="   ",
        )


def test_integration_context_endpoint_rejects_missing_query(
    client,
):
    response = client.post(
        "/integration/context",
        json={},
    )

    assert response.status_code == 422


def test_integration_context_endpoint_rejects_empty_query(
    client,
):
    response = client.post(
        "/integration/context",
        json={
            "query": "",
        },
    )

    assert response.status_code == 422


def test_integration_turn_endpoint_rejects_missing_fields(
    client,
):
    response = client.post(
        "/integration/turn",
        json={},
    )

    assert response.status_code == 422


def test_integration_turn_endpoint_rejects_empty_player_input(
    client,
):
    response = client.post(
        "/integration/turn",
        json={
            "player_input": "",
            "narrative": "Narrativa.",
        },
    )

    assert response.status_code == 422


def test_integration_turn_endpoint_rejects_empty_narrative(
    client,
):
    response = client.post(
        "/integration/turn",
        json={
            "player_input": "Abro la puerta.",
            "narrative": "",
        },
    )

    assert response.status_code == 422

def test_integration_context_endpoint_returns_context(
    client,
    monkeypatch,
):
    def fake_get_context(query):
        assert query == (
            "Entro en la taberna."
        )

        return {
            "campaign": {
                "id": 1,
                "name": "Campaña",
                "system": "D&D 5e 2014",
                "tone": "oscuro",
                "summary": "",
            },
            "session": None,
            "active_character": None,
            "query": "Entro en la taberna.",
            "context": {
                "query": "Entro en la taberna.",
                "context": "Sin información relevante.",
            },
        }

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.get_context",
        fake_get_context,
    )

    response = client.post(
        "/integration/context",
        json={
            "query": "Entro en la taberna.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["campaign"]["id"] == 1

    assert data["query"] == (
        "Entro en la taberna."
    )

    assert data["context"]["context"] == (
        "Sin información relevante."
    )


def test_integration_context_endpoint_returns_500_on_service_error(
    client,
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationServiceError,
    )

    def fake_get_context(query):
        raise SillyTavernIntegrationServiceError(
            "context failed"
        )

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.get_context",
        fake_get_context,
    )

    response = client.post(
        "/integration/context",
        json={
            "query": "Entro en la taberna.",
        },
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": "context failed"
    }


def test_integration_turn_endpoint_returns_processed_turn(
    client,
    monkeypatch,
):
    class FakeResult:
        narrative = (
            "La puerta se abre."
        )

        player_input = (
            "Abro la puerta."
        )

        operation_count = 0

        successful_operation_count = 0

        failed_operation_count = 0

        all_operations_succeeded = True

        world_changed = False

        operations = ()

        character_operations = ()

        operation_results = ()

    def fake_process_turn(
        player_input,
        narrative,
    ):
        assert player_input == (
            "Abro la puerta."
        )

        assert narrative == (
            "La puerta se abre."
        )

        return FakeResult()

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.process_turn",
        fake_process_turn,
    )

    response = client.post(
        "/integration/turn",
        json={
            "player_input": "Abro la puerta.",
            "narrative": "La puerta se abre.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["player_input"] == (
        "Abro la puerta."
    )

    assert data["narrative"] == (
        "La puerta se abre."
    )

    assert data["operation_count"] == 0

    assert data["successful_operation_count"] == 0

    assert data["failed_operation_count"] == 0

    assert data["all_operations_succeeded"] is True

    assert data["world_changed"] is False

    assert data["operations"] == []

    assert data["operation_results"] == []


def test_integration_turn_endpoint_returns_400_on_service_error(
    client,
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationServiceError,
    )

    def fake_process_turn(
        player_input,
        narrative,
    ):
        raise SillyTavernIntegrationServiceError(
            "processing failed"
        )

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.process_turn",
        fake_process_turn,
    )

    response = client.post(
        "/integration/turn",
        json={
            "player_input": "Abro la puerta.",
            "narrative": "La puerta se abre.",
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": "processing failed"
    }

def test_integration_service_uses_context_builder_for_context(
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )

    world_service = WorldService()

    campaign_state_service = (
        CampaignStateService(
            campaign_repository=(
                CampaignRepository()
            ),
            character_repository=(
                CharacterRepository()
            ),
            entity_repository=(
                EntityRepository()
            ),
            world_service=world_service,
        )
    )

    context_builder = ContextBuilder()

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=(
            __import__(
                "services.operation_parser",
                fromlist=["OperationParser"],
            ).OperationParser()
        ),
    )

    turn_repository = TurnRepository()

    service = (
        SillyTavernIntegrationService(
            campaign_state_service=(
                campaign_state_service
            ),
            context_builder=context_builder,
            extractor=extractor,
            world_service=world_service,
            turn_repository=turn_repository,
        )
    )

    calls = []

    def fake_build(
        world,
        query,
        recent_turns=None,
    ):
        calls.append(
            {
                "world": world,
                "query": query,
                "recent_turns": recent_turns,
            }
        )

        return {
            "query": query,
            "context": "CONTEXTO",
        }

    monkeypatch.setattr(
        context_builder,
        "build",
        fake_build,
    )

    result = service.get_context(
        "Entro en la taberna."
    )

    assert result["query"] == (
        "Entro en la taberna."
    )

    assert result["context"] == {
        "query": "Entro en la taberna.",
        "context": "CONTEXTO",
    }

    assert len(calls) == 1

    assert calls[0]["query"] == (
        "Entro en la taberna."
    )

    assert isinstance(
        calls[0]["recent_turns"],
        list,
    )


def test_integration_service_does_not_generate_narrative(
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )
    from services.operation_parser import (
        OperationParser,
    )

    world_service = WorldService()

    campaign_state_service = (
        CampaignStateService(
            campaign_repository=(
                CampaignRepository()
            ),
            character_repository=(
                CharacterRepository()
            ),
            entity_repository=(
                EntityRepository()
            ),
            world_service=world_service,
        )
    )

    context_builder = ContextBuilder()

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = (
        SillyTavernIntegrationService(
            campaign_state_service=(
                campaign_state_service
            ),
            context_builder=context_builder,
            extractor=extractor,
            world_service=world_service,
            turn_repository=turn_repository,
        )
    )

    monkeypatch.setattr(
        extractor,
        "extract",
        lambda narrative, context: [],
    )

    monkeypatch.setattr(
        turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    monkeypatch.setattr(
        turn_repository,
        "save_turn",
        lambda turn: turn,
    )

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        lambda world_operations,
        character_operations: (),
    )

    result = service.process_turn(
        player_input="Abro la puerta.",
        narrative="La puerta se abre.",
    )

    assert result.narrative == (
        "La puerta se abre."
    )

def test_integration_service_passes_silly_tavern_narrative_to_extractor(
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )
    from services.operation_parser import (
        OperationParser,
    )

    world_service = WorldService()

    campaign_state_service = (
        CampaignStateService(
            campaign_repository=(
                CampaignRepository()
            ),
            character_repository=(
                CharacterRepository()
            ),
            entity_repository=(
                EntityRepository()
            ),
            world_service=world_service,
        )
    )

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=OperationParser(),
    )

    service = (
        SillyTavernIntegrationService(
            campaign_state_service=(
                campaign_state_service
            ),
            context_builder=ContextBuilder(),
            extractor=extractor,
            world_service=world_service,
            turn_repository=TurnRepository(),
        )
    )

    captured = {}

    def fake_extract(
        text,
        context,
    ):
        captured["text"] = text
        captured["context"] = context

        return []

    monkeypatch.setattr(
        extractor,
        "extract",
        fake_extract,
    )

    monkeypatch.setattr(
        service.turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    monkeypatch.setattr(
        service.turn_repository,
        "save_turn",
        lambda turn: turn,
    )

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        lambda world_operations,
        character_operations: (),
    )

    service.process_turn(
        player_input="Abro la puerta.",
        narrative=(
            "La puerta se abre y una corriente "
            "helada entra en la habitación."
        ),
    )

    assert captured["text"] == (
        "La puerta se abre y una corriente "
        "helada entra en la habitación."
    )

def test_integration_service_applies_extracted_operations(
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )
    from services.operation_parser import (
        OperationParser,
    )

    world_service = WorldService()

    campaign_state_service = (
        CampaignStateService(
            campaign_repository=(
                CampaignRepository()
            ),
            character_repository=(
                CharacterRepository()
            ),
            entity_repository=(
                EntityRepository()
            ),
            world_service=world_service,
        )
    )

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = (
        SillyTavernIntegrationService(
            campaign_state_service=(
                campaign_state_service
            ),
            context_builder=ContextBuilder(),
            extractor=extractor,
            world_service=world_service,
            turn_repository=turn_repository,
        )
    )

    calls = []

    def fake_apply(
        world_operations,
        character_operations,
    ):
        calls.append(
            {
                "world": world_operations,
                "character": character_operations,
            }
        )

        return ()

    monkeypatch.setattr(
        extractor,
        "extract",
        lambda narrative, context: [],
    )

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        fake_apply,
    )

    monkeypatch.setattr(
        turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    monkeypatch.setattr(
        turn_repository,
        "save_turn",
        lambda turn: turn,
    )

    result = service.process_turn(
        player_input="Miro alrededor.",
        narrative="La habitación permanece en silencio.",
    )

    assert result.operation_count == 0

    assert len(calls) == 1

    assert calls[0]["world"] == []

    assert calls[0]["character"] == []

def test_integration_service_persists_created_entity_from_extracted_operation():
    from operations.world_operations import CreateEntityOperation
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )
    from services.operation_parser import (
        OperationParser,
    )

    world_service = WorldService()

    campaign_state_service = CampaignStateService(
        campaign_repository=CampaignRepository(),
        character_repository=CharacterRepository(),
        entity_repository=EntityRepository(),
        world_service=world_service,
    )

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = SillyTavernIntegrationService(
        campaign_state_service=campaign_state_service,
        context_builder=ContextBuilder(),
        extractor=extractor,
        world_service=world_service,
        turn_repository=turn_repository,
    )

    operation = CreateEntityOperation(
        name="Aldren",
        entity_type="npc",
        description="Propietario de la taberna.",
    )

    extractor.extract = lambda narrative, context: [
        operation
    ]

    result = service.process_turn(
        player_input=(
            "Me acerco al tabernero "
            "y le pregunto su nombre."
        ),
        narrative=(
            "El tabernero se presenta "
            "como Aldren."
        ),
    )

    assert result.operation_count == 1
    assert result.successful_operation_count == 1
    assert result.failed_operation_count == 0
    assert result.all_operations_succeeded is True
    assert result.world_changed is True

    assert len(result.operations) == 1
    assert result.operations[0] == operation

    assert len(result.operation_results) == 1

def test_integration_service_created_entity_is_available_in_context():
    from operations.world_operations import CreateEntityOperation
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )
    from services.operation_parser import (
        OperationParser,
    )

    world_service = WorldService()

    campaign_state_service = CampaignStateService(
        campaign_repository=CampaignRepository(),
        character_repository=CharacterRepository(),
        entity_repository=EntityRepository(),
        world_service=world_service,
    )

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = SillyTavernIntegrationService(
        campaign_state_service=campaign_state_service,
        context_builder=ContextBuilder(),
        extractor=extractor,
        world_service=world_service,
        turn_repository=turn_repository,
    )

    operation = CreateEntityOperation(
        name="Aldren",
        entity_type="npc",
        description="Propietario de la taberna.",
    )

    extractor.extract = lambda narrative, context: [
        operation
    ]

    result = service.process_turn(
        player_input=(
            "Me acerco al tabernero "
            "y le pregunto su nombre."
        ),
        narrative=(
            "El tabernero se presenta "
            "como Aldren."
        ),
    )

    assert result.operation_count == 1
    assert result.successful_operation_count == 1
    assert result.failed_operation_count == 0
    assert result.all_operations_succeeded is True
    assert result.world_changed is True

    turn_context = (
        campaign_state_service.get_turn_context()
    )

    entities = turn_context.world.entities

    aldren = next(
        entity
        for entity in entities.values()
        if entity.name == "Aldren"
    )

    assert aldren.entity_type == "npc"
    assert aldren.description == (
        "Propietario de la taberna."
    )