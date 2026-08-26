from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from models.world_operations_in import WorldOperationsIn
from services.operation_parser import OperationParser, OperationParseError
from services.world_service import WorldService
from services.memory_search_service import MemorySearchService

from database import init_db, one, execute

from models.schemas import (
    CampaignUpdate,
    CampaignSessionUpdate,
    SessionIn,
)

from dataclasses import asdict

app = FastAPI(title="D&D Campaign Manager", version="0.1.0")

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

init_db()

world_service = WorldService()
world_service.load()

memory_search_service = MemorySearchService()

operation_parser = OperationParser()

@app.get("/")
def root():
    return {"ok": True, "service": "D&D Campaign Manager", "version": "0.1.0"}

@app.get("/health")
def health():
    return {"ok": True}

@app.patch("/campaign")
def update_campaign(data: CampaignUpdate):
    current = one("SELECT * FROM campaign WHERE id=1")
    values = {
        "name": data.name if data.name is not None else current["name"],
        "system": data.system if data.system is not None else current["system"],
        "tone": data.tone if data.tone is not None else current["tone"],
        "summary": data.summary if data.summary is not None else current["summary"],
    }
    execute("""UPDATE campaign SET name=?, system=?, tone=?, summary=?,
               updated_at=CURRENT_TIMESTAMP WHERE id=1""",
            (values["name"], values["system"], values["tone"], values["summary"]))
    return one("SELECT * FROM campaign WHERE id=1")


@app.patch("/campaign/session")
def update_campaign_session(data: CampaignSessionUpdate):

    execute(
        """
        UPDATE campaign
        SET current_session_id=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=1
        """,
        (data.session_id,)
    )

    return one("SELECT * FROM campaign WHERE id=1")

@app.post("/sessions")
def create_session(data: SessionIn):
    sid = execute("""INSERT INTO sessions
        (number, title, summary, start_location, end_location, notes)
        VALUES (?, ?, ?, ?, ?, ?)""", tuple(data.model_dump().values()))
    return one("SELECT * FROM sessions WHERE id=?", (sid,))

@app.get("/memory/search")
def search_memory(q: str = Query(..., min_length=1)):
    """
    Busca información relevante dentro del WorldState actual.

    La fuente de verdad es WorldService -> WorldState.
    """

    world = world_service.get_world()

    return memory_search_service.search(
        world,
        q,
    )

@app.get("/memory/context")
def memory_context(q: str = Query(..., min_length=1)):
    """
    Devuelve contexto de memoria para SillyTavern.

    La búsqueda se realiza exclusivamente sobre el WorldState.
    """

    world = world_service.get_world()

    return memory_search_service.context(
        world,
        q,
    )

@app.get("/export")
def export_memory():
    """
    Exporta el estado actual de la campaña.

    WorldState es la única fuente de verdad.
    No se consultan tablas ni estructuras legacy.
    """

    world = world_service.get_world()

    return {
        "entities": [
            asdict(entity)
            for entity in world.entities.values()
        ],
        "items": [
            asdict(item)
            for item in world.items.values()
        ],
        "item_instances": [
            asdict(item_instance)
            for item_instance in world.item_instances.values()
        ],
        "resources": [
            asdict(resource)
            for resource in world.resources.values()
        ],
        "resource_balances": [
            asdict(balance)
            for balance in world.resource_balances.values()
        ],
        "relations": [
            asdict(relation)
            for relation in world.relations.values()
        ],
        "events": [
            asdict(event)
            for event in world.events.values()
        ],
    }

@app.post("/world/operations")
def apply_world_operations(data: WorldOperationsIn):
    """
    Recibe operaciones estructuradas desde SillyTavern,
    las parsea y las aplica al mundo persistente.
    """

    try:
        operations = operation_parser.parse(
            {
                "operations": data.operations
            }
        )

    except OperationParseError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    for operation in operations:
        world_service.apply_operations_and_save(operations)

    return {
        "ok": True,
        "received": len(data.operations),
        "applied": len(operations),
    }

@app.get("/world")
def get_world():
    """
    Devuelve el estado actual del mundo.
    """

    world = world_service.get_world()

    return {
        "entities": list(world.entities.values()),
        "items": list(world.items.values()),
        "item_instances": list(world.item_instances.values()),
        "resources": list(world.resources.values()),
        "resource_balances": list(world.resource_balances.values()),
        "relations": list(world.relations.values()),
        "events": list(world.events.values()),
    }