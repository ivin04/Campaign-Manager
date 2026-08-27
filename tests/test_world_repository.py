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

def test_world_repository_deletes_missing_records(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:

        init_db()
        repository = WorldRepository()

        # --------------------------------------------------------
        # Crear mundo con dependencias
        # --------------------------------------------------------

        fungoso = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        goblin = Entity(
            id=2,
            name="Goblin",
            entity_type="creature",
        )

        sword = Item(
            id=1,
            name="Espada",
        )

        sword_instance = ItemInstance(
            id=1,
            item_id=1,
            instance_number=1,
            owner_id=1,
            location_id=2,
            condition="Buena",
        )

        gold = Resource(
            id=1,
            name="Oro",
            resource_type="currency",
            unit="monedas",
        )

        gold_balance = ResourceBalance(
            id=1,
            resource_id=1,
            owner_id=1,
            amount=100,
        )

        relation = Relation(
            id="fungoso-goblin",
            subject_id=1,
            relation_type="enemy_of",
            target_id=2,
        )

        event = Event(
            id="event-001",
            event_type="discovery",
            title="La espada perdida",
            description="Fungoso encuentra una espada.",
            session_id=None,
            secret=False,
        )

        world = WorldState(
            entities={
                fungoso.id: fungoso,
                goblin.id: goblin,
            },
            items={
                sword.id: sword,
            },
            item_instances={
                sword_instance.id: sword_instance,
            },
            resources={
                gold.id: gold,
            },
            resource_balances={
                gold_balance.id: gold_balance,
            },
            relations={
                relation.id: relation,
            },
            events={
                event.id: event,
            },
        )

        # --------------------------------------------------------
        # Primer SAVE
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # Eliminar todo del estado en memoria
        # --------------------------------------------------------

        world.events.clear()
        world.relations.clear()
        world.item_instances.clear()
        world.resource_balances.clear()
        world.items.clear()
        world.resources.clear()
        world.entities.clear()

        # --------------------------------------------------------
        # Segundo SAVE
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # Comprobar que SQLite quedó vacío
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert loaded.entities == {}
        assert loaded.items == {}
        assert loaded.item_instances == {}
        assert loaded.resources == {}
        assert loaded.resource_balances == {}
        assert loaded.relations == {}
        assert loaded.events == {}

    finally:

        database.DB_PATH = original_db_path

def test_world_repository_can_delete_entity_with_dependencies(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:

        init_db()
        repository = WorldRepository()

        entity_a = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        entity_b = Entity(
            id=2,
            name="Goblin",
            entity_type="creature",
        )

        item = Item(
            id=1,
            name="Espada",
        )

        item_instance = ItemInstance(
            id=1,
            item_id=1,
            instance_number=1,
            owner_id=1,
        )

        resource = Resource(
            id=1,
            name="Oro",
            resource_type="currency",
        )

        balance = ResourceBalance(
            id=1,
            resource_id=1,
            owner_id=1,
            amount=50,
        )

        relation = Relation(
            id="relation-001",
            subject_id=1,
            relation_type="enemy_of",
            target_id=2,
        )

        world = WorldState(
            entities={
                1: entity_a,
                2: entity_b,
            },
            items={
                1: item,
            },
            item_instances={
                1: item_instance,
            },
            resources={
                1: resource,
            },
            resource_balances={
                1: balance,
            },
            relations={
                "relation-001": relation,
            },
        )

        # Guardamos el mundo completo.
        repository.save_world(world)

        # --------------------------------------------------------
        # Eliminamos SOLO Fungoso
        # --------------------------------------------------------

        del world.entities[1]

        # --------------------------------------------------------
        # Debe poder persistirse sin error de FK
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # Comprobar resultado
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert 1 not in loaded.entities

        # La instancia queda huérfana y no debe persistirse.
        assert 1 not in loaded.item_instances

        # El balance pertenecía a Fungoso.
        assert 1 not in loaded.resource_balances

        # La relación tenía a Fungoso como subject.
        assert "relation-001" not in loaded.relations

        # El Goblin sigue existiendo.
        assert 2 in loaded.entities

        # El item y el recurso siguen existiendo porque no eran
        # propiedad exclusiva de la entidad en el modelo.
        assert 1 in loaded.items
        assert 1 in loaded.resources

    finally:

        database.DB_PATH = original_db_path

def test_world_repository_can_delete_item_with_instances(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:

        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        item = Item(
            id=1,
            name="Espada",
        )

        item_instance = ItemInstance(
            id=1,
            item_id=1,
            instance_number=1,
            owner_id=1,
        )

        world = WorldState(
            entities={
                1: entity,
            },
            items={
                1: item,
            },
            item_instances={
                1: item_instance,
            },
        )

        # --------------------------------------------------------
        # Guardar
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # Eliminar el Item del estado
        # --------------------------------------------------------

        del world.items[1]

        # --------------------------------------------------------
        # Guardar de nuevo
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # Comprobar
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert 1 not in loaded.items
        assert 1 not in loaded.item_instances

        # La entidad no debe desaparecer.
        assert 1 in loaded.entities

    finally:

        database.DB_PATH = original_db_path

def test_save_world_is_atomic_when_persistence_fails(tmp_path, monkeypatch):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        world = WorldState(
            entities={
                1: entity,
            }
        )

        # Primera persistencia válida.
        repository.save_world(world)

        # Nuevo estado que queremos intentar guardar.
        entity_2 = Entity(
            id=2,
            name="Goblin",
            entity_type="creature",
        )

        world.entities[2] = entity_2

        def failing_save_entities(conn, world):
            raise RuntimeError("Database failure")

        monkeypatch.setattr(
            repository,
            "_save_entities",
            failing_save_entities,
        )

        # La operación debe fallar.
        try:
            repository.save_world(world)
        except RuntimeError:
            pass

        # --------------------------------------------------------
        # La base de datos debe seguir exactamente como antes.
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert 1 in loaded.entities
        assert 2 not in loaded.entities

    finally:
        database.DB_PATH = original_db_path

def test_save_world_normalizes_dependencies_before_persisting(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        item = Item(
            id=1,
            name="Espada",
        )

        item_instance = ItemInstance(
            id=1,
            item_id=1,
            instance_number=1,
            owner_id=1,
        )

        world = WorldState(
            entities={1: entity},
            items={1: item},
            item_instances={1: item_instance},
        )

        repository.save_world(world)

        # Eliminamos el item del snapshot.
        del world.items[1]

        # La instancia queda temporalmente huérfana
        # dentro del WorldState.
        assert 1 in world.item_instances

        repository.save_world(world)

        # El WorldState original NO debe ser mutado por el repository.
        assert 1 in world.item_instances

        # Pero la instancia huérfana NO debe haberse persistido.
        loaded = repository.load_world()

        assert 1 not in loaded.item_instances

        loaded = repository.load_world()

        assert loaded.items == {}
        assert loaded.item_instances == {}
        assert loaded.entities == {
            1: entity,
        }

    finally:
        database.DB_PATH = original_db_path

def test_save_world_removes_balance_when_resource_is_missing(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        resource = Resource(
            id=1,
            name="Oro",
            resource_type="currency",
        )

        balance = ResourceBalance(
            id=1,
            resource_id=1,
            owner_id=1,
            amount=100,
        )

        world = WorldState(
            entities={1: entity},
            resources={1: resource},
            resource_balances={1: balance},
        )

        repository.save_world(world)

        del world.resources[1]

        assert 1 in world.resource_balances

        repository.save_world(world)

        # El WorldState original no debe ser mutado.
        assert 1 in world.resource_balances

        # Pero el balance huérfano no debe persistirse.
        loaded = repository.load_world()

        assert 1 not in loaded.resource_balances

        loaded = repository.load_world()

        assert loaded.resources == {}
        assert loaded.resource_balances == {}
        assert loaded.entities == {
            1: entity,
        }

    finally:
        database.DB_PATH = original_db_path

def test_save_world_removes_relation_when_entity_is_missing(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity_a = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        entity_b = Entity(
            id=2,
            name="Goblin",
            entity_type="creature",
        )

        relation = Relation(
            id="relation-001",
            subject_id=1,
            relation_type="enemy_of",
            target_id=2,
        )

        world = WorldState(
            entities={
                1: entity_a,
                2: entity_b,
            },
            relations={
                "relation-001": relation,
            },
        )

        repository.save_world(world)

        del world.entities[1]

        assert "relation-001" in world.relations

        repository.save_world(world)

        # El WorldState original no debe ser mutado.
        assert "relation-001" in world.relations

        # Pero la relación huérfana no debe persistirse.
        loaded = repository.load_world()

        assert "relation-001" not in loaded.relations

        loaded = repository.load_world()

        assert loaded.entities == {
            2: entity_b,
        }

        assert loaded.relations == {}

    finally:
        database.DB_PATH = original_db_path

def test_save_world_empty_snapshot_clears_persisted_world(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        item = Item(
            id=1,
            name="Espada",
        )

        resource = Resource(
            id=1,
            name="Oro",
            resource_type="currency",
        )

        world = WorldState(
            entities={1: entity},
            items={1: item},
            resources={1: resource},
        )

        repository.save_world(world)

        empty_world = WorldState()

        repository.save_world(empty_world)

        loaded = repository.load_world()

        assert loaded.entities == {}
        assert loaded.items == {}
        assert loaded.item_instances == {}
        assert loaded.resources == {}
        assert loaded.resource_balances == {}
        assert loaded.relations == {}
        assert loaded.events == {}

    finally:
        database.DB_PATH = original_db_path

def test_save_world_is_idempotent(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        item = Item(
            id=1,
            name="Espada",
        )

        instance = ItemInstance(
            id=1,
            item_id=1,
            instance_number=1,
            owner_id=1,
        )

        world = WorldState(
            entities={1: entity},
            items={1: item},
            item_instances={1: instance},
        )

        repository.save_world(world)

        first = repository.load_world()

        repository.save_world(world)

        second = repository.load_world()

        assert second == first

    finally:
        database.DB_PATH = original_db_path

def test_save_world_is_atomic_when_persistence_fails(monkeypatch, tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        world = WorldState(
            entities={
                1: entity,
            }
        )

        # Estado inicial vacío.
        repository.save_world(WorldState())

        # Forzamos un fallo DESPUÉS de haber empezado a guardar.
        original_save_items = repository._save_items

        def failing_save_items(conn, world):
            original_save_items(conn, world)
            raise RuntimeError("Database failure")

        monkeypatch.setattr(
            repository,
            "_save_items",
            failing_save_items,
        )

        try:
            repository.save_world(world)
        except RuntimeError:
            pass

        # --------------------------------------------------------
        # La transacción debe haber hecho rollback.
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert loaded.entities == {}
        assert loaded.items == {}

    finally:
        database.DB_PATH = original_db_path

def test_save_world_removes_records_missing_from_world(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        world = WorldState(
            entities={
                1: entity,
            }
        )

        # --------------------------------------------------------
        # Primera persistencia
        # --------------------------------------------------------

        repository.save_world(world)

        loaded = repository.load_world()

        assert 1 in loaded.entities

        # --------------------------------------------------------
        # Eliminamos la entidad del WorldState
        # --------------------------------------------------------

        del world.entities[1]

        # --------------------------------------------------------
        # Segunda persistencia
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # SQLite debe reflejar exactamente el nuevo estado
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert loaded.entities == {}

    finally:
        database.DB_PATH = original_db_path

def test_save_world_removes_missing_relations_and_events(tmp_path):

    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    try:
        init_db()
        repository = WorldRepository()

        entity_a = Entity(
            id=1,
            name="Fungoso",
            entity_type="character",
        )

        entity_b = Entity(
            id=2,
            name="Goblin",
            entity_type="creature",
        )

        relation = Relation(
            id="relation-001",
            subject_id=1,
            relation_type="enemy_of",
            target_id=2,
        )

        event = Event(
            id="event-001",
            event_type="discovery",
            title="La espada perdida",
        )

        world = WorldState(
            entities={
                1: entity_a,
                2: entity_b,
            },
            relations={
                relation.id: relation,
            },
            events={
                event.id: event,
            },
        )

        # --------------------------------------------------------
        # Persistir estado inicial
        # --------------------------------------------------------

        repository.save_world(world)

        loaded = repository.load_world()

        assert "relation-001" in loaded.relations
        assert "event-001" in loaded.events

        # --------------------------------------------------------
        # Eliminamos ambos del WorldState
        # --------------------------------------------------------

        del world.relations["relation-001"]
        del world.events["event-001"]

        # --------------------------------------------------------
        # Persistimos nuevamente
        # --------------------------------------------------------

        repository.save_world(world)

        # --------------------------------------------------------
        # Deben haber desaparecido de SQLite
        # --------------------------------------------------------

        loaded = repository.load_world()

        assert loaded.relations == {}
        assert loaded.events == {}

        # Las entidades siguen existiendo.
        assert 1 in loaded.entities
        assert 2 in loaded.entities

    finally:
        database.DB_PATH = original_db_path

def test_save_world_rolls_back_deletes_when_later_save_fails(monkeypatch):
    from database import get_conn
    from repositories.world_repository import WorldRepository
    from models.world_state import WorldState
    from models.entity import Entity

    repository = WorldRepository()

    # Estado inicial persistido.
    original_world = WorldState()

    original_world.entities[1] = Entity(
        id=1,
        name="Entity To Be Deleted",
        entity_type="character",
        description="original",
        notes="",
        active=True,
    )

    original_world.entities[2] = Entity(
        id=2,
        name="Entity To Keep",
        entity_type="character",
        description="original",
        notes="",
        active=True,
    )

    repository.save_world(original_world)

    # Nuevo estado:
    # - entity 1 desaparece → el repository tendrá que hacer DELETE.
    # - entity 2 permanece.
    new_world = WorldState()

    new_world.entities[2] = Entity(
        id=2,
        name="Entity To Keep",
        entity_type="character",
        description="modified",
        notes="",
        active=True,
    )

    # Provocamos un fallo después de que save_world()
    # haya empezado a modificar la base de datos.
    def failing_save_items(conn, world):
        raise RuntimeError("forced persistence failure")

    monkeypatch.setattr(
        repository,
        "_save_items",
        failing_save_items,
    )

    try:
        repository.save_world(new_world)
    except RuntimeError:
        pass
    else:
        raise AssertionError(
            "save_world() should have raised RuntimeError"
        )

    # La transacción debe haber hecho rollback.
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id, name, description "
            "FROM entities "
            "ORDER BY id"
        ).fetchall()

    assert len(rows) == 2

    assert rows[0]["id"] == 1
    assert rows[0]["name"] == "Entity To Be Deleted"
    assert rows[0]["description"] == "original"

    assert rows[1]["id"] == 2
    assert rows[1]["name"] == "Entity To Keep"
    assert rows[1]["description"] == "original"

def test_save_world_does_not_mutate_world_when_persistence_fails(monkeypatch):
    from repositories.world_repository import WorldRepository
    from models.world_state import WorldState
    from models.entity import Entity
    from models.relation import Relation

    repository = WorldRepository()

    world = WorldState()

    world.entities[1] = Entity(
        id=1,
        name="Entity To Keep",
        entity_type="character",
        description="original",
        notes="",
        active=True,
    )

    world.relations["relation-1"] = Relation(
        id="relation-1",
        subject_id=1,
        target_id=999,
        relation_type="enemy_of",
        metadata={},
    )

    original_relations = dict(world.relations)

    def failing_save_events(conn, world_to_save):
        raise RuntimeError("forced persistence failure")

    monkeypatch.setattr(
        repository,
        "_save_events",
        failing_save_events,
    )

    try:
        repository.save_world(world)
    except RuntimeError:
        pass
    else:
        raise AssertionError(
            "save_world() should have raised RuntimeError"
        )

    assert world.relations == original_relations
    assert "relation-1" in world.relations

def test_next_entity_id_does_not_reuse_deleted_ids():
    from models.world_state import WorldState
    from models.entity import Entity
    from services.world_applier import WorldApplier

    world = WorldState(
        entities={
            1: Entity(
                id=1,
                name="One",
                entity_type="character",
            ),
            2: Entity(
                id=2,
                name="Two",
                entity_type="character",
            ),
            3: Entity(
                id=3,
                name="Three",
                entity_type="character",
            ),
        }
    )

    del world.entities[3]

    assert WorldApplier._next_entity_id(world) == 3