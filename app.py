from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from models.world_operations_in import WorldOperationsIn
from services.operation_parser import OperationParser, OperationParseError
from services.world_service import WorldService
from services.memory_search_service import MemorySearchService

from database import init_db, rows, one, execute

from models.schemas import (
    CampaignUpdate,
    CampaignSessionUpdate,
    ItemIn,
    EventIn,
    SessionIn,
)

from repositories import item_repository
from services import item_service

import re

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

@app.get("/campaign")
def get_campaign():
    return one("SELECT * FROM campaign WHERE id=1")

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

@app.post("/items/extracted")
def save_extracted_item(data: ItemIn):
    try:
        from services.item_service import save_extracted_item

        item = save_extracted_item(
            data.model_dump()
        )

        return item

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        print(
            "[campaign-manager] ERROR saving extracted item:",
            repr(e)
        )

        raise HTTPException(
            status_code=500,
            detail="Could not save extracted item"
        )

@app.get("/items/search")
def search_item(name: str = Query(..., min_length=1)):
    item = item_service.get_item_by_name(name)

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    return item

@app.put("/items/{item_id}")
def update_item(item_id: int, data: ItemIn):
    item = item_service.get_item(item_id)

    if not item:
        raise HTTPException(
            status_code=404,
            detail="Item not found"
        )

    item_service.update_item(
        item_id,
        data.model_dump()
    )

    return item_service.get_item(item_id)

@app.get("/items")
def get_items(q: Optional[str] = None):
    if q:
        return item_service.search_items(q)

    return item_service.get_all_items()

@app.post("/events")
def create_event(data: EventIn):
    try:
        d = data.model_dump()

        # Evitar duplicados de eventos esencialmente iguales.
        existing = one("""
            SELECT *
            FROM events
            WHERE LOWER(TRIM(title)) = LOWER(TRIM(?))
              AND LOWER(TRIM(description)) = LOWER(TRIM(?))
            LIMIT 1
        """, (
            d["title"],
            d["description"],
        ))

        if existing:
            print(
                "[campaign-manager] Event already exists, skipping:",
                d["title"]
            )

            return existing

        eid = execute("""
            INSERT INTO events
            (title, session, event_type, description, consequences, secret)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            d["title"],
            d["session"],
            d["event_type"],
            d["description"],
            d["consequences"],
            int(bool(d["secret"]))
        ))

        event = one(
            "SELECT * FROM events WHERE id=?",
            (eid,)
        )

        print(
            "[campaign-manager] Event saved:",
            event
        )

        return event

    except Exception as e:
        print(
            "[campaign-manager] ERROR creating event:",
            repr(e)
        )
        raise

@app.get("/events/search")
def search_event(title: str = Query(..., min_length=1)):
    event = one("""
        SELECT *
        FROM events
        WHERE LOWER(title) = LOWER(?)
        LIMIT 1
    """, (title.strip(),))

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    return event


@app.put("/events/{event_id}")
def update_event(event_id: int, data: EventIn):
    event = one(
        "SELECT * FROM events WHERE id=?",
        (event_id,)
    )

    if not event:
        raise HTTPException(
            status_code=404,
            detail="Event not found"
        )

    d = data.model_dump()

    execute("""
        UPDATE events
        SET title=?,
            session=?,
            event_type=?,
            description=?,
            consequences=?,
            secret=?
        WHERE id=?
    """, (
        d["title"],
        d["session"],
        d["event_type"],
        d["description"],
        d["consequences"],
        int(bool(d["secret"])),
        event_id
    ))

    return one(
        "SELECT * FROM events WHERE id=?",
        (event_id,)
    )

@app.get("/events")
def get_events(session: Optional[int] = None, q: Optional[str] = None):
    if session is not None:
        return rows("SELECT * FROM events WHERE session=? ORDER BY id", (session,))
    if q:
        like = f"%{q}%"
        return rows("""SELECT * FROM events WHERE title LIKE ? OR description LIKE ?
                       OR consequences LIKE ? ORDER BY id""", (like, like, like))
    return rows("SELECT * FROM events ORDER BY id")

@app.post("/sessions")
def create_session(data: SessionIn):
    sid = execute("""INSERT INTO sessions
        (number, title, summary, start_location, end_location, notes)
        VALUES (?, ?, ?, ?, ?, ?)""", tuple(data.model_dump().values()))
    return one("SELECT * FROM sessions WHERE id=?", (sid,))

@app.get("/sessions")
def get_sessions():
    return rows("SELECT * FROM sessions ORDER BY number")

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
    return {
        "campaign": get_campaign(),
        "characters": get_characters(),
        "locations": get_locations(),
        "factions": get_factions(),
        "quests": get_quests(),
        "items": get_items(),
        "events": get_events(),
        "sessions": get_sessions(),
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
        world_service.apply_and_save(operation)

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