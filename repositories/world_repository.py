import json

from database import get_conn, rows
from models.world_state import WorldState
from models.entity import Entity
from models.item import Item, ItemInstance
from models.resource import Resource, ResourceBalance
from models.relation import Relation
from models.event import Event


class WorldRepository:

    # ============================================================
    # LOAD
    # ============================================================

    def load_world(self) -> WorldState:

        world = WorldState()

        self._load_entities(world)
        self._load_items(world)
        self._load_item_instances(world)
        self._load_resources(world)
        self._load_resource_balances(world)
        self._load_relations(world)
        self._load_events(world)

        return world

    def _load_entities(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                name,
                entity_type,
                description,
                notes,
                active
            FROM entities
        """)

        for row in rows_data:

            entity = Entity(
                id=row["id"],
                name=row["name"],
                entity_type=row["entity_type"],
                description=row["description"],
                notes=row["notes"],
                active=bool(row["active"]),
            )

            world.entities[entity.id] = entity

    def _load_items(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                name,
                description,
                significance,
                unique_item,
                notes
            FROM items
        """)

        for row in rows_data:

            item = Item(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                significance=row["significance"],
                unique=bool(row["unique_item"]),
                notes=row["notes"],
            )

            world.items[item.id] = item

    def _load_item_instances(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                item_id,
                instance_number,
                owner_id,
                location_id,
                condition,
                notes,
                active
            FROM item_instances
        """)

        for row in rows_data:

            instance = ItemInstance(
                id=row["id"],
                item_id=row["item_id"],
                instance_number=row["instance_number"],
                owner_id=row["owner_id"],
                location_id=row["location_id"],
                condition=row["condition"],
                notes=row["notes"],
                active=bool(row["active"]),
            )

            world.item_instances[instance.id] = instance

    def _load_resources(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                name,
                resource_type,
                unit,
                notes
            FROM resources
        """)

        for row in rows_data:

            resource = Resource(
                id=row["id"],
                name=row["name"],
                resource_type=row["resource_type"],
                unit=row["unit"],
                notes=row["notes"],
            )

            world.resources[resource.id] = resource

    def _load_resource_balances(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                resource_id,
                owner_id,
                amount,
                notes
            FROM resource_balances
        """)

        for row in rows_data:

            balance = ResourceBalance(
                id=row["id"],
                resource_id=row["resource_id"],
                owner_id=row["owner_id"],
                amount=row["amount"],
                notes=row["notes"],
            )

            world.resource_balances[balance.id] = balance

    def _load_relations(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                subject_id,
                relation_type,
                target_id,
                metadata,
                active
            FROM relations
        """)

        for row in rows_data:

            relation = Relation(
                id=row["id"],
                subject_id=row["subject_id"],
                relation_type=row["relation_type"],
                target_id=row["target_id"],
                metadata=json.loads(row["metadata"])
                    if row["metadata"] is not None
                    else None,
                active=bool(row["active"]),
            )

            world.relations[relation.id] = relation

    def _load_events(self, world: WorldState):

        rows_data = rows("""
            SELECT
                id,
                event_type,
                title,
                description,
                consequences,
                session_id,
                secret,
                metadata
            FROM world_events
        """)

        for row in rows_data:

            event = Event(
                id=row["id"],
                event_type=row["event_type"],
                title=row["title"],
                description=row["description"],
                consequences=row["consequences"],
                session_id=row["session_id"],
                secret=bool(row["secret"]),
                metadata=json.loads(row["metadata"])
                    if row["metadata"] is not None
                    else {},
            )

            world.events[event.id] = event

    # ============================================================
    # SAVE
    # ============================================================

    def save_world(self, world: WorldState):

        with get_conn() as conn:

            self._save_entities(conn, world)
            self._save_items(conn, world)
            self._save_item_instances(conn, world)
            self._save_resources(conn, world)
            self._save_resource_balances(conn, world)
            self._save_relations(conn, world)
            self._save_events(conn, world)

    # ============================================================
    # SAVE ENTITIES
    # ============================================================

    def _save_entities(self, conn, world: WorldState):

        for entity in world.entities.values():

            conn.execute("""
                INSERT INTO entities (
                    id,
                    name,
                    entity_type,
                    description,
                    notes,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    entity_type = excluded.entity_type,
                    description = excluded.description,
                    notes = excluded.notes,
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                entity.id,
                entity.name,
                entity.entity_type,
                entity.description,
                entity.notes,
                int(entity.active),
            ))

    # ============================================================
    # SAVE ITEMS
    # ============================================================

    def _save_items(self, conn, world: WorldState):

        for item in world.items.values():

            conn.execute("""
                INSERT INTO items (
                    id,
                    name,
                    description,
                    significance,
                    unique_item,
                    notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    significance = excluded.significance,
                    unique_item = excluded.unique_item,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                item.id,
                item.name,
                item.description,
                item.significance,
                int(item.unique),
                item.notes,
            ))

    # ============================================================
    # SAVE ITEM INSTANCES
    # ============================================================

    def _save_item_instances(self, conn, world: WorldState):

        for instance in world.item_instances.values():

            conn.execute("""
                INSERT INTO item_instances (
                    id,
                    item_id,
                    instance_number,
                    owner_id,
                    location_id,
                    condition,
                    notes,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    item_id = excluded.item_id,
                    instance_number = excluded.instance_number,
                    owner_id = excluded.owner_id,
                    location_id = excluded.location_id,
                    condition = excluded.condition,
                    notes = excluded.notes,
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                instance.id,
                instance.item_id,
                instance.instance_number,
                instance.owner_id,
                instance.location_id,
                instance.condition,
                instance.notes,
                int(instance.active),
            ))

    # ============================================================
    # SAVE RESOURCES
    # ============================================================

    def _save_resources(self, conn, world: WorldState):

        for resource in world.resources.values():

            conn.execute("""
                INSERT INTO resources (
                    id,
                    name,
                    resource_type,
                    unit,
                    notes
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    resource_type = excluded.resource_type,
                    unit = excluded.unit,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                resource.id,
                resource.name,
                resource.resource_type,
                resource.unit,
                resource.notes,
            ))

    # ============================================================
    # SAVE RESOURCE BALANCES
    # ============================================================

    def _save_resource_balances(self, conn, world: WorldState):

        for balance in world.resource_balances.values():

            conn.execute("""
                INSERT INTO resource_balances (
                    id,
                    resource_id,
                    owner_id,
                    amount,
                    notes
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    resource_id = excluded.resource_id,
                    owner_id = excluded.owner_id,
                    amount = excluded.amount,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                balance.id,
                balance.resource_id,
                balance.owner_id,
                balance.amount,
                balance.notes,
            ))

    # ============================================================
    # SAVE RELATIONS
    # ============================================================

    def _save_relations(self, conn, world: WorldState):

        for relation in world.relations.values():

            metadata = json.dumps(
                relation.metadata
            ) if relation.metadata is not None else None

            conn.execute("""
                INSERT INTO relations (
                    id,
                    subject_id,
                    relation_type,
                    target_id,
                    metadata,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    subject_id = excluded.subject_id,
                    relation_type = excluded.relation_type,
                    target_id = excluded.target_id,
                    metadata = excluded.metadata,
                    active = excluded.active,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                relation.id,
                relation.subject_id,
                relation.relation_type,
                relation.target_id,
                metadata,
                int(relation.active),
            ))

    # ============================================================
    # SAVE EVENTS
    # ============================================================

    def _save_events(self, conn, world: WorldState):

        for event in world.events.values():

            metadata = json.dumps(
                event.metadata
            ) if event.metadata is not None else None

            conn.execute("""
                INSERT INTO world_events (
                    id,
                    event_type,
                    title,
                    description,
                    consequences,
                    session_id,
                    secret,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    event_type = excluded.event_type,
                    title = excluded.title,
                    description = excluded.description,
                    consequences = excluded.consequences,
                    session_id = excluded.session_id,
                    secret = excluded.secret,
                    metadata = excluded.metadata,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                event.id,
                event.event_type,
                event.title,
                event.description,
                event.consequences,
                event.session_id,
                int(event.secret),
                metadata,
            ))