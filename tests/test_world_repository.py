import json

import database
from database import init_db
from models.entity import Entity
from models.event import Event
from models.item import Item, ItemInstance
from models.relation import Relation
from models.resource import Resource, ResourceBalance
from models.world_state import WorldState
from repositories.world_repository import WorldRepository


def test_world_repository_round_trip(tmp_path):

    # ------------------------------------------------------------
    # Usar una SQLite temporal
    # ------------------------------------------------------------

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:

        init_db()

        repository = WorldRepository()

        # --------------------------------------------------------
        # Crear entidades
        # --------------------------------------------------------

        fungoso = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
            description="Un aventurero peculiar.",
            notes="Le gusta el oro.",
            active=True,
        )

        goblin = Entity(
            id=2,
            name="Goblin",
            entity_type="creature",
            description="Un goblin hostil.",
            notes="Vive cerca de la mina.",
            active=True,
        )

        world = WorldState(
            entities={
                fungoso.id: fungoso,
                goblin.id: goblin,
            }
        )

        # --------------------------------------------------------
        # Item
        # --------------------------------------------------------

        sword = Item(
            id=1,
            name="Espada de hierro",
            description="Una espada sencilla.",
            significance="Común",
            unique=False,
            notes="Tiene una pequeña muesca.",
        )

        world.items[sword.id] = sword

        # --------------------------------------------------------
        # Item instance
        # --------------------------------------------------------

        sword_instance = ItemInstance(
            id=1,
            item_id=1,
            instance_number=1,
            owner_id=1,
            location_id=None,
            condition="Buena",
            notes="Pertenece a Fungoso.",
            active=True,
        )

        world.item_instances[sword_instance.id] = sword_instance

        # --------------------------------------------------------
        # Resource
        # --------------------------------------------------------

        gold = Resource(
            id=1,
            name="Oro",
            resource_type="currency",
            unit="monedas",
            notes="Moneda habitual.",
        )

        world.resources[gold.id] = gold

        # --------------------------------------------------------
        # Resource balance
        # --------------------------------------------------------

        gold_balance = ResourceBalance(
            id=1,
            resource_id=1,
            owner_id=1,
            amount=100,
            notes="Oro de Fungoso.",
        )

        world.resource_balances[gold_balance.id] = gold_balance

        # --------------------------------------------------------
        # Relation
        # --------------------------------------------------------

        relation = Relation(
            id="fungoso-goblin-enemy",
            subject_id=1,
            relation_type="enemy_of",
            target_id=2,
            metadata={
                "reason": "Intentó robarle",
                "strength": 80,
            },
            active=True,
        )

        world.relations[relation.id] = relation

        # --------------------------------------------------------
        # Event
        # --------------------------------------------------------

        event = Event(
            id="event-001",
            event_type="discovery",
            title="La espada perdida",
            description="Fungoso encuentra una espada.",
            consequences="Ahora posee la espada.",
            session_id=1,
            secret=False,
            metadata={
                "importance": "medium",
                "location": "mina",
            },
        )

        world.events[event.id] = event

        # --------------------------------------------------------
        # SAVE
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # LOAD
        # --------------------------------------------------------

        loaded = repository.load_world()

        # --------------------------------------------------------
        # ENTITIES
        # --------------------------------------------------------

        assert loaded.entities == world.entities

        # --------------------------------------------------------
        # ITEMS
        # --------------------------------------------------------

        assert loaded.items == world.items

        # --------------------------------------------------------
        # ITEM INSTANCES
        # --------------------------------------------------------

        assert loaded.item_instances == world.item_instances

        # --------------------------------------------------------
        # RESOURCES
        # --------------------------------------------------------

        assert loaded.resources == world.resources

        # --------------------------------------------------------
        # RESOURCE BALANCES
        # --------------------------------------------------------

        assert loaded.resource_balances == world.resource_balances

        # --------------------------------------------------------
        # RELATIONS
        # --------------------------------------------------------

        assert loaded.relations == world.relations

        # --------------------------------------------------------
        # EVENTS
        # --------------------------------------------------------

        assert loaded.events == world.events

    finally:

        database.DB_PATH = original_db_path