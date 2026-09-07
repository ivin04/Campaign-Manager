import pytest

from models.campaign_state import CampaignState
from models.turn_context import TurnContext
from models.world_state import WorldState
from services.llm_world_extractor import LLMWorldExtractor
from services.ollama_provider import OllamaProvider
from services.operation_parser import OperationParser

pytestmark = pytest.mark.real_llm


def make_context() -> TurnContext:
    return TurnContext(
        campaign=CampaignState(),
        current_session=None,
        active_character=None,
        world=WorldState(),
    )

def test_real_ollama_extractor_returns_valid_operations():
    provider = OllamaProvider()

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=OperationParser(),
    )

    context = make_context()

    narrative = (
        "El aventurero entra en una pequeña taberna de piedra. "
        "El tabernero se presenta como Aldric y le entrega "
        "una llave de hierro oxidada."
    )

    operations = extractor.extract(
        narrative,
        context,
    )

    assert isinstance(operations, list)

    print("\n=== OPERACIONES EXTRAÍDAS POR OLLAMA ===")

    for index, operation in enumerate(operations, start=1):
        print(f"{index}. {operation!r}")

    print("=== FIN DE OPERACIONES ===")

    operation_types = [
        type(operation).__name__
        for operation in operations
    ]

    print("\n=== TIPOS DE OPERACIÓN ===")
    print(operation_types)
    print("=== FIN DE TIPOS ===\n")

    for operation in operations:
        assert operation is not None

def test_real_ollama_full_turn_persists_world_change():
    from database import get_conn
    from repositories.campaign_repository import CampaignRepository
    from repositories.character_repository import CharacterRepository
    from repositories.entity_repository import EntityRepository
    from repositories.turn_repository import TurnRepository
    from services.campaign_state_service import CampaignStateService
    from services.context_builder import ContextBuilder
    from services.llm_world_extractor import LLMWorldExtractor
    from services.ollama_provider import OllamaProvider
    from services.operation_parser import OperationParser
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.world_service import WorldService

    world_service = WorldService()
    world_service.load()

    campaign_state_service = CampaignStateService(
        campaign_repository=CampaignRepository(),
        character_repository=CharacterRepository(),
        entity_repository=EntityRepository(),
        world_service=world_service,
    )

    context_builder = ContextBuilder()

    extractor = LLMWorldExtractor(
        provider=OllamaProvider(),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = SillyTavernIntegrationService(
        campaign_state_service=campaign_state_service,
        context_builder=context_builder,
        extractor=extractor,
        world_service=world_service,
        turn_repository=turn_repository,
    )

    narrative = (
        "El aventurero llega a una pequeña taberna de piedra. "
        "El tabernero se presenta como Aldric y le entrega "
        "una llave de hierro oxidada."
    )

    result = service.process_turn(
        external_turn_id="real-ollama-e2e-001",
        turn_version=1,
        player_input="Entro en la taberna y hablo con el tabernero.",
        narrative=narrative,
    )

    assert result is not None
    assert result.narrative

    with get_conn() as conn:
        aldric = conn.execute(
            """
            SELECT id, name, entity_type
            FROM entities
            WHERE name = ?
            """,
            ("Aldric",),
        ).fetchone()

        key = conn.execute(
            """
            SELECT id, name
            FROM items
            WHERE name = ?
            """,
            ("Llave de hierro",),
        ).fetchone()

        turn = conn.execute(
            """
            SELECT id, external_turn_id, version
            FROM turns
            WHERE external_turn_id = ?
            """,
            ("real-ollama-e2e-001",),
        ).fetchone()

    assert aldric is not None
    assert aldric["entity_type"] == "npc"

    assert key is not None

    assert turn is not None
    assert turn["external_turn_id"] == "real-ollama-e2e-001"
    assert turn["version"] == 1

def test_real_ollama_regeneration_restores_previous_snapshot():
    from database import get_conn
    from repositories.campaign_repository import CampaignRepository
    from repositories.character_repository import CharacterRepository
    from repositories.entity_repository import EntityRepository
    from repositories.turn_repository import TurnRepository
    from services.campaign_state_service import CampaignStateService
    from services.context_builder import ContextBuilder
    from services.llm_world_extractor import LLMWorldExtractor
    from services.ollama_provider import OllamaProvider
    from services.operation_parser import OperationParser
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.world_service import WorldService

    world_service = WorldService()

    campaign_state_service = CampaignStateService(
        campaign_repository=CampaignRepository(),
        character_repository=CharacterRepository(),
        entity_repository=EntityRepository(),
        world_service=world_service,
    )

    context_builder = ContextBuilder()

    extractor = LLMWorldExtractor(
        provider=OllamaProvider(),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = SillyTavernIntegrationService(
        campaign_state_service=campaign_state_service,
        context_builder=context_builder,
        extractor=extractor,
        world_service=world_service,
        turn_repository=turn_repository,
    )

    # --------------------------------------------------------
    # V1
    # --------------------------------------------------------

    v1_narrative = (
        "El aventurero entra en una pequeña taberna de piedra. "
        "El tabernero se presenta como Aldric y le entrega "
        "una llave de hierro oxidada."
    )

    v1 = service.process_turn(
        player_input=(
            "Entro en la taberna y hablo con el tabernero."
        ),
        narrative=v1_narrative,
        external_turn_id="real-ollama-regeneration-001",
        turn_version=1,
    )

    assert v1 is not None
    assert v1.narrative == v1_narrative

    # --------------------------------------------------------
    # Comprobar que V1 realmente modificó el mundo.
    # --------------------------------------------------------

    with get_conn() as conn:
        aldric_v1 = conn.execute(
            """
            SELECT id
            FROM entities
            WHERE name = ?
            """,
            ("Aldric",),
        ).fetchone()

        key_v1 = conn.execute(
            """
            SELECT id
            FROM items
            WHERE name = ?
            """,
            ("Llave de hierro",),
        ).fetchone()

    assert aldric_v1 is not None
    assert key_v1 is not None

    # --------------------------------------------------------
    # Regeneración V2.
    #
    # Esta narrativa NO menciona a Aldric ni la llave.
    # El snapshot de V1 debe restaurarse antes de aplicar V2.
    # --------------------------------------------------------

    v2_narrative = (
        "El aventurero decide ignorar al tabernero "
        "y continúa hacia una habitación lateral. "
        "Allí encuentra a una mujer llamada Mira "
        "que vigila una puerta cerrada."
    )

    v2 = service.process_turn(
        player_input=(
            "Ignoro al tabernero y exploro la habitación lateral."
        ),
        narrative=v2_narrative,
        external_turn_id="real-ollama-regeneration-001",
        turn_version=2,
    )

    assert v2 is not None
    assert v2.narrative == v2_narrative

    # --------------------------------------------------------
    # Estado final.
    #
    # Aldric y la llave pertenecen al estado de V1.
    # Mira pertenece al estado de V2.
    #
    # Lo importante es que el mundo final no haya acumulado
    # modificaciones de V1 + V2 de forma incorrecta.
    # --------------------------------------------------------

    with get_conn() as conn:
        aldric_final = conn.execute(
            """
            SELECT id
            FROM entities
            WHERE name = ?
            """,
            ("Aldric",),
        ).fetchone()

        key_final = conn.execute(
            """
            SELECT id
            FROM items
            WHERE name = ?
            """,
            ("Llave de hierro",),
        ).fetchone()

        mira_final = conn.execute(
            """
            SELECT id
            FROM entities
            WHERE name = ?
            """,
            ("Mira",),
        ).fetchone()

        turns = conn.execute(
            """
            SELECT external_turn_id, version, status
            FROM turns
            WHERE external_turn_id = ?
            ORDER BY version
            """,
            ("real-ollama-regeneration-001",),
        ).fetchall()

    # --------------------------------------------------------
    # V1 debe haber sido completamente sustituido por V2.
    #
    # El snapshot almacenado en V1 representa el estado
    # anterior a V1. Al regenerar V2 se restaura ese estado
    # y después se aplican únicamente las operaciones de V2.
    # --------------------------------------------------------

    assert aldric_final is None
    assert key_final is None

    # Mira pertenece exclusivamente a V2.
    assert mira_final is not None

    assert len(turns) == 2

    assert turns[0]["version"] == 1
    assert turns[1]["version"] == 2