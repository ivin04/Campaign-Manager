import json

from database import rows, one, execute

from models.entity import Entity
from models.item import Item, ItemInstance
from models.resource import Resource, ResourceBalance
from models.relation import Relation
from models.event import Event
from models.world_state import WorldState


class WorldRepository:

    # =========================================================
    # LOAD
    # =========================================================

    def load_world(self) -> WorldState:
        """
        Carga el estado completo del mundo desde SQLite.

        Este repositorio utiliza exclusivamente el nuevo modelo
        de dominio. No debe depender de ninguna tabla legacy.
        """

        world = WorldState()

        self._load_entities(world)
        self._load_items(world)
        self._load_item_instances(world)
        self._load_resources(world)
        self._load_resource_balances(world)
        self._load_relations(world)
        self._load_events(world)

        return world

    # =========================================================
    # ENTITIES
    # =========================================================

    def _load_entities(
        self,
        world: WorldState,
    ) -> None:

        entity_rows = rows(
            """
            SELECT
                id,
                name,
                entity_type,
                description,
                notes,
                active
            FROM entities
            ORDER BY id
            """
        )

        for row in entity_rows:

            entity = Entity(
                id=row["id"],
                name=row["name"],
                entity_type=row["entity_type"] or "",
                description=row["description"] or "",
                notes=row["notes"] or "",
                active=bool(row["active"]),
            )

            if entity.id is None:
                continue

            world.entities[entity.id] = entity

    # =========================================================
    # ITEMS
    # =========================================================

    def _load_items(
        self,
        world: WorldState,
    ) -> None:

        item_rows = rows(
            """
            SELECT
                id,
                name,
                description,
                significance,
                unique_item,
                notes
            FROM items
            ORDER BY id
            """
        )

        for row in item_rows:

            item = Item(
                id=row["id"],
                name=row["name"],
                description=row["description"] or "",
                significance=row["significance"] or "",
                unique=bool(row["unique_item"]),
                notes=row["notes"] or "",
            )

            if item.id is None:
                continue

            world.items[item.id] = item

    # =========================================================
    # ITEM INSTANCES
    # =========================================================

    def _load_item_instances(
        self,
        world: WorldState,
    ) -> None:

        instance_rows = rows(
            """
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
            ORDER BY id
            """
        )

        for row in instance_rows:

            instance = ItemInstance(
                id=row["id"],
                item_id=row["item_id"],
                instance_number=row["instance_number"],
                owner_id=row["owner_id"],
                location_id=row["location_id"],
                condition=row["condition"] or "",
                notes=row["notes"] or "",
                active=bool(row["active"]),
            )

            if instance.id is None:
                continue

            world.item_instances[
                instance.id
            ] = instance

    # =========================================================
    # RESOURCES
    # =========================================================

    def _load_resources(
        self,
        world: WorldState,
    ) -> None:

        resource_rows = rows(
            """
            SELECT
                id,
                name,
                resource_type,
                unit,
                notes
            FROM resources
            ORDER BY id
            """
        )

        for row in resource_rows:

            resource = Resource(
                id=row["id"],
                name=row["name"],
                resource_type=row["resource_type"] or "generic",
                unit=row["unit"] or "",
                notes=row["notes"] or "",
            )

            if resource.id is None:
                continue

            world.resources[
                resource.id
            ] = resource

    # =========================================================
    # RESOURCE BALANCES
    # =========================================================

    def _load_resource_balances(
        self,
        world: WorldState,
    ) -> None:

        balance_rows = rows(
            """
            SELECT
                id,
                resource_id,
                owner_id,
                amount,
                notes
            FROM resource_balances
            ORDER BY id
            """
        )

        for row in balance_rows:

            balance = ResourceBalance(
                id=row["id"],
                resource_id=row["resource_id"],
                owner_id=row["owner_id"],
                amount=float(row["amount"]),
                notes=row["notes"] or "",
            )

            if balance.id is None:
                continue

            world.resource_balances[
                balance.id
            ] = balance

    # =========================================================
    # RELATIONS
    # =========================================================

    def _load_relations(
        self,
        world: WorldState,
    ) -> None:

        relation_rows = rows(
            """
            SELECT
                id,
                subject_id,
                relation_type,
                target_id,
                metadata,
                active
            FROM relations
            ORDER BY id
            """
        )

        for row in relation_rows:

            metadata = self._deserialize_metadata(
                row["metadata"]
            )

            relation = Relation(
                id=str(row["id"]),
                subject_id=row["subject_id"],
                relation_type=row["relation_type"],
                target_id=row["target_id"],
                metadata=metadata,
                active=bool(row["active"]),
            )

            world.relations[
                relation.id
            ] = relation

    # =========================================================
    # EVENTS
    # =========================================================

    def _load_events(
        self,
        world: WorldState,
    ) -> None:

        event_rows = rows(
            """
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
            ORDER BY created_at, id
            """
        )

        for row in event_rows:

            metadata = self._deserialize_metadata(
                row["metadata"]
            )

            event = Event(
                id=str(row["id"]),
                event_type=row["event_type"] or "",
                title=row["title"],
                description=row["description"] or "",
                consequences=row["consequences"] or "",
                session_id=row["session_id"],
                secret=bool(row["secret"]),
                metadata=metadata or {},
            )

            world.events[
                event.id
            ] = event

    # =========================================================
    # SAVE
    # =========================================================

    def save_world(
        self,
        world: WorldState,
    ) -> None:
        """
        Persiste el WorldState completo.

        El repositorio es responsable de traducir el modelo
        de dominio a SQLite.

        No contiene reglas de negocio.
        """

        self._save_entities(world)
        self._save_items(world)
        self._save_item_instances(world)
        self._save_resources(world)
        self._save_resource_balances(world)
        self._save_relations(world)
        self._save_events(world)

    # =========================================================
    # SAVE ENTITIES
    # =========================================================

    def _save_entities(
        self,
        world: WorldState,
    ) -> None:

        for entity in list(world.entities.values()):

            if entity.id is None:

                entity_id = execute(
                    """
                    INSERT INTO entities
                        (
                            name,
                            entity_type,
                            description,
                            notes,
                            active
                        )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        entity.name,
                        entity.entity_type,
                        entity.description,
                        entity.notes,
                        int(entity.active),
                    )
                )

                entity.id = entity_id

            else:

                execute(
                    """
                    UPDATE entities
                    SET
                        name=?,
                        entity_type=?,
                        description=?,
                        notes=?,
                        active=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        entity.name,
                        entity.entity_type,
                        entity.description,
                        entity.notes,
                        int(entity.active),
                        entity.id,
                    )
                )

    # =========================================================
    # SAVE ITEMS
    # =========================================================

    def _save_items(
        self,
        world: WorldState,
    ) -> None:

        for item in list(world.items.values()):

            if item.id is None:

                item_id = execute(
                    """
                    INSERT INTO items
                        (
                            name,
                            description,
                            significance,
                            unique_item,
                            notes
                        )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        item.name,
                        item.description,
                        item.significance,
                        int(item.unique),
                        item.notes,
                    )
                )

                item.id = item_id

            else:

                execute(
                    """
                    UPDATE items
                    SET
                        name=?,
                        description=?,
                        significance=?,
                        unique_item=?,
                        notes=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        item.name,
                        item.description,
                        item.significance,
                        int(item.unique),
                        item.notes,
                        item.id,
                    )
                )

    # =========================================================
    # SAVE ITEM INSTANCES
    # =========================================================

    def _save_item_instances(
        self,
        world: WorldState,
    ) -> None:

        for instance in list(
            world.item_instances.values()
        ):

            if instance.id is None:

                instance_id = execute(
                    """
                    INSERT INTO item_instances
                        (
                            item_id,
                            instance_number,
                            owner_id,
                            location_id,
                            condition,
                            notes,
                            active
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        instance.item_id,
                        instance.instance_number,
                        instance.owner_id,
                        instance.location_id,
                        instance.condition,
                        instance.notes,
                        int(instance.active),
                    )
                )

                instance.id = instance_id

            else:

                execute(
                    """
                    UPDATE item_instances
                    SET
                        item_id=?,
                        instance_number=?,
                        owner_id=?,
                        location_id=?,
                        condition=?,
                        notes=?,
                        active=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        instance.item_id,
                        instance.instance_number,
                        instance.owner_id,
                        instance.location_id,
                        instance.condition,
                        instance.notes,
                        int(instance.active),
                        instance.id,
                    )
                )

    # =========================================================
    # SAVE RESOURCES
    # =========================================================

    def _save_resources(
        self,
        world: WorldState,
    ) -> None:

        for resource in list(
            world.resources.values()
        ):

            if resource.id is None:

                resource_id = execute(
                    """
                    INSERT INTO resources
                        (
                            name,
                            resource_type,
                            unit,
                            notes
                        )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        resource.name,
                        resource.resource_type,
                        resource.unit,
                        resource.notes,
                    )
                )

                resource.id = resource_id

            else:

                execute(
                    """
                    UPDATE resources
                    SET
                        name=?,
                        resource_type=?,
                        unit=?,
                        notes=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        resource.name,
                        resource.resource_type,
                        resource.unit,
                        resource.notes,
                        resource.id,
                    )
                )

    # =========================================================
    # SAVE RESOURCE BALANCES
    # =========================================================

    def _save_resource_balances(
        self,
        world: WorldState,
    ) -> None:

        for balance in list(
            world.resource_balances.values()
        ):

            if balance.id is None:

                balance_id = execute(
                    """
                    INSERT INTO resource_balances
                        (
                            resource_id,
                            owner_id,
                            amount,
                            notes
                        )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        balance.resource_id,
                        balance.owner_id,
                        balance.amount,
                        balance.notes,
                    )
                )

                balance.id = balance_id

            else:

                execute(
                    """
                    UPDATE resource_balances
                    SET
                        resource_id=?,
                        owner_id=?,
                        amount=?,
                        notes=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        balance.resource_id,
                        balance.owner_id,
                        balance.amount,
                        balance.notes,
                        balance.id,
                    )
                )

    # =========================================================
    # SAVE RELATIONS
    # =========================================================

    def _save_relations(
        self,
        world: WorldState,
    ) -> None:

        for relation in list(
            world.relations.values()
        ):

            if not relation.id:
                continue

            metadata = self._serialize_metadata(
                relation.metadata
            )

            existing = one(
                """
                SELECT id
                FROM relations
                WHERE id=?
                """,
                (relation.id,)
            )

            if existing:

                execute(
                    """
                    UPDATE relations
                    SET
                        subject_id=?,
                        relation_type=?,
                        target_id=?,
                        metadata=?,
                        active=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        relation.subject_id,
                        relation.relation_type,
                        relation.target_id,
                        metadata,
                        int(relation.active),
                        relation.id,
                    )
                )

            else:

                execute(
                    """
                    INSERT INTO relations
                        (
                            id,
                            subject_id,
                            relation_type,
                            target_id,
                            metadata,
                            active
                        )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        relation.id,
                        relation.subject_id,
                        relation.relation_type,
                        relation.target_id,
                        metadata,
                        int(relation.active),
                    )
                )

    # =========================================================
    # SAVE EVENTS
    # =========================================================

    def _save_events(
        self,
        world: WorldState,
    ) -> None:

        for event in list(
            world.events.values()
        ):

            if not event.id:
                continue

            metadata = self._serialize_metadata(
                event.metadata
            )

            existing = one(
                """
                SELECT id
                FROM world_events
                WHERE id=?
                """,
                (event.id,)
            )

            if existing:

                execute(
                    """
                    UPDATE world_events
                    SET
                        event_type=?,
                        title=?,
                        description=?,
                        consequences=?,
                        session_id=?,
                        secret=?,
                        metadata=?,
                        updated_at=CURRENT_TIMESTAMP
                    WHERE id=?
                    """,
                    (
                        event.event_type,
                        event.title,
                        event.description,
                        event.consequences,
                        event.session_id,
                        int(event.secret),
                        metadata,
                        event.id,
                    )
                )

            else:

                execute(
                    """
                    INSERT INTO world_events
                        (
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
                    """,
                    (
                        event.id,
                        event.event_type,
                        event.title,
                        event.description,
                        event.consequences,
                        event.session_id,
                        int(event.secret),
                        metadata,
                    )
                )

    # =========================================================
    # METADATA
    # =========================================================

    @staticmethod
    def _serialize_metadata(
        metadata: dict | None,
    ) -> str | None:

        if metadata is None:
            return None

        return json.dumps(
            metadata,
            ensure_ascii=False,
        )

    @staticmethod
    def _deserialize_metadata(
        value,
    ) -> dict | None:

        if value is None:
            return None

        if isinstance(value, dict):
            return value

        if not isinstance(value, str):
            return None

        value = value.strip()

        if not value:
            return None

        try:
            decoded = json.loads(value)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None

        if not isinstance(decoded, dict):
            return None

        return decoded