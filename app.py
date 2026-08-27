from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from database import init_db

from models.schemas import (
    CampaignUpdate,
    CampaignSessionUpdate,
    SessionIn,
    TurnIn,
)

from repositories.campaign_repository import CampaignRepository

from services.campaign_turn_service import (
    CampaignTurnService,
    CampaignTurnServiceError,
)
from services.context_builder import ContextBuilder
from services.dm_service import DMService
from services.llm_world_extractor import LLMWorldExtractor
from services.memory_search_service import MemorySearchService
from services.ollama_provider import OllamaProvider
from services.operation_parser import (
    OperationParser,
)
from services.turn_resolution_service import (
    TurnResolutionService,
)
from services.world_service import WorldService


app = FastAPI(
    title="D&D Campaign Manager",
    version="0.1.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# APPLICATION SERVICES
# ============================================================


def create_world_service() -> WorldService:
    """
    Crea el WorldService y carga el WorldState persistido.
    """

    init_db()

    service = WorldService()

    service.load()

    return service


def create_campaign_turn_service(
    world_service: WorldService,
) -> CampaignTurnService:
    """
    Construye el pipeline completo de resolución de turnos.

    Flujo:

        jugador
          ↓
        CampaignTurnService
          ↓
        TurnResolutionService
          ↓
        DMService
          ↓
        Ollama
          ↓
        narrativa
          ↓
        LLMWorldExtractor
          ↓
        operaciones
          ↓
        WorldApplier
          ↓
        WorldService
          ↓
        SQLite
    """

    provider = OllamaProvider()

    operation_parser = OperationParser()

    context_builder = ContextBuilder(
        memory_search_service=memory_search_service,
    )

    dm_service = DMService(
        provider=provider,
        context_builder=context_builder,
    )

    extractor = LLMWorldExtractor(
        provider=provider,
        operation_parser=operation_parser,
    )
    
    turn_resolution_service = TurnResolutionService(
        dm_service=dm_service,
        extractor=extractor,
        world_service=world_service,
    )

    return CampaignTurnService(
        turn_resolution_service=turn_resolution_service,
        world_service=world_service,
    )


# ============================================================
# SINGLETON APPLICATION STATE
# ============================================================


world_service = create_world_service()

campaign_repository = CampaignRepository()

memory_search_service = MemorySearchService()

campaign_turn_service = create_campaign_turn_service(
    world_service
)


# ============================================================
# BASIC
# ============================================================


@app.get("/")
def root():
    return {
        "ok": True,
        "service": "D&D Campaign Manager",
        "version": "0.1.0",
    }


@app.get("/health")
def health():
    return {
        "ok": True,
    }


# ============================================================
# CAMPAIGN
# ============================================================


@app.patch("/campaign")
def update_campaign(data: CampaignUpdate):

    current = campaign_repository.get_campaign()

    values = {
        "name": (
            data.name
            if data.name is not None
            else current["name"]
        ),
        "system": (
            data.system
            if data.system is not None
            else current["system"]
        ),
        "tone": (
            data.tone
            if data.tone is not None
            else current["tone"]
        ),
        "summary": (
            data.summary
            if data.summary is not None
            else current["summary"]
        ),
    }

    return campaign_repository.update_campaign(
        campaign_id=1,
        **values,
    )


@app.patch("/campaign/session")
def update_campaign_session(
    data: CampaignSessionUpdate,
):

    return campaign_repository.update_current_session(
        campaign_id=1,
        session_id=data.session_id,
    )


@app.post("/sessions")
def create_session(data: SessionIn):

    return campaign_repository.create_session(
        **data.model_dump()
    )


# ============================================================
# TURN
# ============================================================


@app.post("/turn")
def play_turn(data: TurnIn):

    try:
        result = campaign_turn_service.play_turn(
            data.player_input
        )

    except CampaignTurnServiceError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    return {
        "narrative": result.narrative,
        "player_input": result.player_input,
        "operation_count": result.operation_count,
        "successful_operation_count": (
            result.successful_operation_count
        ),
        "failed_operation_count": (
            result.failed_operation_count
        ),
        "all_operations_succeeded": (
            result.all_operations_succeeded
        ),
        "world_changed": result.world_changed,
        "operations": [
            type(operation).__name__
            for operation in result.operations
        ],
        "operation_results": [
            _serialize_operation_result(
                operation_result
            )
            for operation_result
            in result.operation_results
        ],
    }


# ============================================================
# MEMORY
# ============================================================


@app.get("/memory/search")
def search_memory(
    q: str = Query(..., min_length=1),
):
    """
    Busca información relevante dentro del
    WorldState actual.
    """

    world = world_service.get_world()

    return memory_search_service.search(
        world,
        q,
    )


@app.get("/memory/context")
def memory_context(q: str):

    world = world_service.get_world()

    context_builder = ContextBuilder(
        memory_search_service=memory_search_service,
    )

    return context_builder.build(
        world,
        q,
    )


# ============================================================
# WORLD
# ============================================================


@app.get("/world")
def get_world():
    """
    Devuelve el estado actual del mundo.
    """

    world = world_service.get_world()

    return {
        "entities": list(
            world.entities.values()
        ),
        "items": list(
            world.items.values()
        ),
        "item_instances": list(
            world.item_instances.values()
        ),
        "resources": list(
            world.resources.values()
        ),
        "resource_balances": list(
            world.resource_balances.values()
        ),
        "relations": list(
            world.relations.values()
        ),
        "events": list(
            world.events.values()
        ),
    }

# ============================================================
# EXPORT
# ============================================================


@app.get("/export")
def export_memory():
    """
    Exporta el estado actual de la campaña.

    WorldState es la única fuente de verdad.
    """

    world = world_service.get_world()

    return {
        "entities": [
            asdict(entity)
            for entity
            in world.entities.values()
        ],
        "items": [
            asdict(item)
            for item
            in world.items.values()
        ],
        "item_instances": [
            asdict(item_instance)
            for item_instance
            in world.item_instances.values()
        ],
        "resources": [
            asdict(resource)
            for resource
            in world.resources.values()
        ],
        "resource_balances": [
            asdict(balance)
            for balance
            in world.resource_balances.values()
        ],
        "relations": [
            asdict(relation)
            for relation
            in world.relations.values()
        ],
        "events": [
            asdict(event)
            for event
            in world.events.values()
        ],
    }


# ============================================================
# SERIALIZATION
# ============================================================


def _serialize_operation_result(
    result,
):
    return {
        "status": result.status.value,
        "message": result.message,
        "operation": (
            type(result.operation).__name__
            if result.operation is not None
            else None
        ),
    }