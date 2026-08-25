from models.entity import Entity
from models.event import Event
from models.item import Item
from models.world_state import WorldState
from services.world_memory_service import WorldMemoryService


class FakeWorldService:

    def __init__(self, world):
        self.world = world

    def get_world(self):
        return self.world


def build_service(world):
    return WorldMemoryService(
        FakeWorldService(world)
    )


def test_search_finds_entity():

    world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
                description="Un aventurero peculiar.",
                notes="Le gusta el oro.",
                active=True,
            )
        }
    )

    service = build_service(world)

    result = service.search("Fungoso")

    assert len(result["entities"]) == 1
    assert result["entities"][0]["name"] == "Fungoso"


def test_search_does_not_return_inactive_entities():

    world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="Goblin muerto",
                entity_type="creature",
                description="Un goblin derrotado.",
                active=False,
            )
        }
    )

    service = build_service(world)

    result = service.search("Goblin")

    assert result["entities"] == []


def test_search_finds_item():

    world = WorldState(
        items={
            1: Item(
                id=1,
                name="Espada de hierro",
                description="Una espada sencilla.",
                significance="Común",
                unique=False,
                notes="Tiene una muesca.",
            )
        }
    )

    service = build_service(world)

    result = service.search("espada")

    assert len(result["items"]) == 1
    assert result["items"][0]["name"] == "Espada de hierro"


def test_search_does_not_expose_secret_events():

    world = WorldState(
        events={
            "secret-001": Event(
                id="secret-001",
                event_type="secret",
                title="El verdadero origen del rey",
                description="El rey es un impostor.",
                consequences="El jugador todavía no lo sabe.",
                session_id=1,
                secret=True,
                metadata={
                    "importance": "critical",
                },
            )
        }
    )

    service = build_service(world)

    result = service.search("rey")

    assert result["events"] == []


def test_search_finds_public_event():

    world = WorldState(
        events={
            "event-001": Event(
                id="event-001",
                event_type="discovery",
                title="La mina abandonada",
                description="Los aventureros descubren una mina.",
                consequences="Se abre una nueva zona.",
                session_id=2,
                secret=False,
                metadata={
                    "location": "Vorder's Hold",
                },
            )
        }
    )

    service = build_service(world)

    result = service.search("mina")

    assert len(result["events"]) == 1
    assert result["events"][0]["id"] == "event-001"


def test_export_contains_only_public_world_state():

    world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
                description="Aventurero.",
                active=True,
            )
        },
        events={
            "public": Event(
                id="public",
                event_type="discovery",
                title="Descubrimiento",
                description="Algo ocurrió.",
                consequences="Nada especial.",
                session_id=1,
                secret=False,
            ),
            "secret": Event(
                id="secret",
                event_type="secret",
                title="El gran secreto",
                description="Información secreta.",
                consequences="Nadie lo sabe.",
                session_id=1,
                secret=True,
            ),
        },
    )

    service = build_service(world)

    result = service.export()

    assert len(result["entities"]) == 1
    assert len(result["events"]) == 1
    assert result["events"][0]["id"] == "public"


def test_context_wraps_memory_search():

    world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="Fungoso",
                entity_type="character",
                description="Aventurero.",
                active=True,
            )
        }
    )

    service = build_service(world)

    result = service.context("Fungoso")

    assert result["query"] == "Fungoso"
    assert len(result["memory"]["entities"]) == 1


def test_empty_query_returns_empty_memory():

    world = WorldState()

    service = build_service(world)

    result = service.search("")

    assert result == {
        "entities": [],
        "items": [],
        "item_instances": [],
        "resources": [],
        "resource_balances": [],
        "relations": [],
        "events": [],
    }