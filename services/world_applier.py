import math

from models.world_state import WorldState
from models.relation import Relation
from models.event import Event
from models.resource import ResourceBalance
from models.entity import Entity

from operations.world_operations import (
    WorldOperation,
    CreateEntityOperation,
    UpdateEntityOperation,
    TransferItemOperation,
    GainResourceOperation,
    SpendResourceOperation,
    TransferResourceOperation,
    CreateRelationOperation,
    UpdateRelationOperation,
    RemoveRelationOperation,
    CreateEventOperation,
)


class WorldApplier:
    """
    Aplica operaciones de dominio sobre un WorldState.

    WorldApplier:
        - modifica únicamente el estado en memoria
        - no accede a SQLite
        - no persiste cambios
        - no genera operaciones nuevas

    La persistencia corresponde a WorldService/WorldRepository.
    """

    def apply(
        self,
        world: WorldState,
        operation: WorldOperation,
    ) -> None:

        if isinstance(operation, CreateEntityOperation):
            self._apply_create_entity(world, operation)

        elif isinstance(operation, UpdateEntityOperation):
            self._apply_update_entity(world, operation)

        elif isinstance(operation, TransferItemOperation):
            self._apply_transfer_item(world, operation)

        elif isinstance(operation, GainResourceOperation):
            self._apply_gain_resource(world, operation)

        elif isinstance(operation, SpendResourceOperation):
            self._apply_spend_resource(world, operation)

        elif isinstance(operation, TransferResourceOperation):
            self._apply_transfer_resource(world, operation)

        elif isinstance(operation, CreateRelationOperation):
            self._apply_create_relation(world, operation)

        elif isinstance(operation, UpdateRelationOperation):
            self._apply_update_relation(world, operation)

        elif isinstance(operation, RemoveRelationOperation):
            self._apply_remove_relation(world, operation)

        elif isinstance(operation, CreateEventOperation):
            self._apply_create_event(world, operation)

    # ============================================================
    # ENTITIES
    # ============================================================

    def _apply_create_entity(
        self,
        world: WorldState,
        operation: CreateEntityOperation,
    ) -> None:

        name = operation.name.strip()

        if not name:
            return

        # Evitar duplicados por nombre.
        for entity in world.entities.values():
            if entity.name.strip().lower() == name.lower():
                return

        entity_id = self._next_entity_id(world)

        world.entities[entity_id] = Entity(
            id=entity_id,
            name=name,
            entity_type=operation.entity_type,
            description=operation.description,
            notes=operation.notes,
            active=operation.active,
        )

    def _apply_update_entity(
        self,
        world: WorldState,
        operation: UpdateEntityOperation,
    ) -> None:

        entity = world.entities.get(operation.entity_id)

        if entity is None:
            return

        if operation.name is not None:
            name = operation.name.strip()

            if not name:
                return

            for entity_id, other in world.entities.items():
                if entity_id == operation.entity_id:
                    continue

                if other.name.strip().lower() == name.lower():
                    return

            entity.name = name

        if operation.entity_type is not None:
            entity.entity_type = operation.entity_type

        if operation.description is not None:
            entity.description = operation.description

        if operation.notes is not None:
            entity.notes = operation.notes

        if operation.active is not None:
            entity.active = operation.active

    # ============================================================
    # ITEMS
    # ============================================================

    def _apply_transfer_item(
        self,
        world: WorldState,
        operation: TransferItemOperation,
    ) -> None:

        instance = world.item_instances.get(operation.instance_id)

        if instance is None:
            return

        if operation.new_owner_id not in world.entities:
            return

        if instance.owner_id == operation.new_owner_id:
            return

        instance.owner_id = operation.new_owner_id

    # ============================================================
    # RESOURCES
    # ============================================================

    def _apply_gain_resource(
        self,
        world: WorldState,
        operation: GainResourceOperation,
    ) -> None:

        if operation.resource_id not in world.resources:
            return

        if operation.owner_id not in world.entities:
            return

        if not self._valid_amount(operation.amount):
            return

        balance = self._find_balance(
            world,
            operation.resource_id,
            operation.owner_id,
        )

        if balance is not None:
            balance.amount += operation.amount
            return

        balance_id = self._next_balance_id(world)

        world.resource_balances[balance_id] = ResourceBalance(
            id=balance_id,
            resource_id=operation.resource_id,
            owner_id=operation.owner_id,
            amount=operation.amount,
        )

    def _apply_spend_resource(
        self,
        world: WorldState,
        operation: SpendResourceOperation,
    ) -> None:

        if operation.resource_id not in world.resources:
            return

        if operation.owner_id not in world.entities:
            return

        if not self._valid_amount(operation.amount):
            return

        balance = self._find_balance(
            world,
            operation.resource_id,
            operation.owner_id,
        )

        if balance is None:
            return

        if balance.amount < operation.amount:
            return

        balance.amount -= operation.amount

    def _apply_transfer_resource(
        self,
        world: WorldState,
        operation: TransferResourceOperation,
    ) -> None:

        if operation.resource_id not in world.resources:
            return

        if operation.source_id not in world.entities:
            return

        if operation.target_id not in world.entities:
            return

        if not self._valid_amount(operation.amount):
            return

        source_balance = self._find_balance(
            world,
            operation.resource_id,
            operation.source_id,
        )

        if source_balance is None:
            return

        if source_balance.amount < operation.amount:
            return

        target_balance = self._find_balance(
            world,
            operation.resource_id,
            operation.target_id,
        )

        if target_balance is None:

            balance_id = self._next_balance_id(world)

            target_balance = ResourceBalance(
                id=balance_id,
                resource_id=operation.resource_id,
                owner_id=operation.target_id,
                amount=0,
            )

            world.resource_balances[balance_id] = target_balance

        source_balance.amount -= operation.amount
        target_balance.amount += operation.amount

    # ============================================================
    # RELATIONS
    # ============================================================

    def _apply_create_relation(
        self,
        world: WorldState,
        operation: CreateRelationOperation,
    ) -> None:

        if operation.relation_id in world.relations:
            return

        if not operation.relation_type:
            return

        subject_id = self._coerce_entity_id(
            operation.subject_id
        )

        target_id = self._coerce_entity_id(
            operation.target_id
        )

        if subject_id is None or target_id is None:
            return

        if subject_id not in world.entities:
            return

        if target_id not in world.entities:
            return

        world.relations[operation.relation_id] = Relation(
            id=operation.relation_id,
            subject_id=subject_id,
            relation_type=operation.relation_type,
            target_id=target_id,
            metadata=operation.metadata,
            active=True,
        )

    def _apply_update_relation(
        self,
        world: WorldState,
        operation: UpdateRelationOperation,
    ) -> None:

        relation = world.relations.get(operation.relation_id)

        if relation is None:
            return

        if operation.relation_type is not None:

            if not operation.relation_type:
                return

            relation.relation_type = operation.relation_type

        if operation.target_id is not None:

            target_id = self._coerce_entity_id(
                operation.target_id
            )

            if target_id is None:
                return

            if target_id not in world.entities:
                return

            relation.target_id = target_id

        if operation.metadata is not None:
            relation.metadata = operation.metadata

        if operation.active is not None:
            relation.active = operation.active

    def _apply_remove_relation(
        self,
        world: WorldState,
        operation: RemoveRelationOperation,
    ) -> None:

        relation = world.relations.get(
            operation.relation_id
        )

        if relation is None:
            return

        relation.active = False

    # ============================================================
    # EVENTS
    # ============================================================

    def _apply_create_event(
        self,
        world: WorldState,
        operation: CreateEventOperation,
    ) -> None:

        if not operation.event_id:
            return

        if not operation.event_type:
            return

        if not operation.title:
            return

        if operation.event_id in world.events:
            return

        world.events[operation.event_id] = Event(
            id=operation.event_id,
            event_type=operation.event_type,
            title=operation.title,
            description=operation.description,
            consequences=operation.consequences,
            session_id=operation.session_id,
            secret=operation.secret,
            metadata=operation.metadata or {},
        )

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _next_entity_id(
        world: WorldState,
    ) -> int:

        numeric_ids = [
            entity_id
            for entity_id in world.entities
            if isinstance(entity_id, int)
            and not isinstance(entity_id, bool)
        ]

        return max(numeric_ids, default=0) + 1

    @staticmethod
    def _valid_amount(amount: float) -> bool:

        if isinstance(amount, bool):
            return False

        if not isinstance(amount, (int, float)):
            return False

        if not math.isfinite(amount):
            return False

        return amount > 0

    @staticmethod
    def _coerce_entity_id(value) -> int | None:

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _find_balance(
        world: WorldState,
        resource_id: int,
        owner_id: int,
    ) -> ResourceBalance | None:

        for balance in world.resource_balances.values():

            if (
                balance.resource_id == resource_id
                and balance.owner_id == owner_id
            ):
                return balance

        return None

    @staticmethod
    def _next_balance_id(
        world: WorldState,
    ) -> int:

        numeric_ids = [
            balance_id
            for balance_id in world.resource_balances
            if isinstance(balance_id, int)
            and not isinstance(balance_id, bool)
        ]

        return max(numeric_ids, default=0) + 1