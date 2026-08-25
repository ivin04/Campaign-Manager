from models.world_state import WorldState
from models.relation import Relation
from models.event import Event
from models.resource import ResourceBalance

from operations.world_operations import (
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

    def apply(
        self,
        world: WorldState,
        operation,
    ) -> None:

        if isinstance(operation, TransferItemOperation):
            self._apply_transfer_item(
                world,
                operation,
            )

        elif isinstance(operation, GainResourceOperation):
            self._apply_gain_resource(
                world,
                operation,
            )

        elif isinstance(operation, SpendResourceOperation):
            self._apply_spend_resource(
                world,
                operation,
            )

        elif isinstance(operation, TransferResourceOperation):
            self._apply_transfer_resource(
                world,
                operation,
            )

        elif isinstance(operation, CreateRelationOperation):
            self._apply_create_relation(
                world,
                operation,
            )

        elif isinstance(operation, UpdateRelationOperation):
            self._apply_update_relation(
                world,
                operation,
            )

        elif isinstance(operation, RemoveRelationOperation):
            self._apply_remove_relation(
                world,
                operation,
            )

        elif isinstance(operation, CreateEventOperation):
            self._apply_create_event(
                world,
                operation,
            )

    # ---------------------------------------------------------
    # ITEM
    # ---------------------------------------------------------

    def _apply_transfer_item(
        self,
        world: WorldState,
        operation: TransferItemOperation,
    ) -> None:

        instance = world.item_instances.get(
            operation.instance_id
        )

        if not instance:
            return

        if operation.new_owner_id not in world.entities:
            return

        if instance.owner_id == operation.new_owner_id:
            return

        instance.owner_id = operation.new_owner_id

    # ---------------------------------------------------------
    # RESOURCES
    # ---------------------------------------------------------

    def _apply_gain_resource(
        self,
        world: WorldState,
        operation: GainResourceOperation,
    ) -> None:

        if operation.resource_id not in world.resources:
            return

        if operation.owner_id not in world.entities:
            return

        if operation.amount <= 0:
            return

        balance = next(
            (
                balance
                for balance in world.resource_balances.values()
                if balance.resource_id == operation.resource_id
                and balance.owner_id == operation.owner_id
            ),
            None,
        )

        if balance is not None:
            balance.amount += operation.amount
            return

        balance_id = (
            max(world.resource_balances.keys(), default=0) + 1
        )

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

        if operation.amount <= 0:
            return

        balance = next(
            (
                balance
                for balance in world.resource_balances.values()
                if balance.resource_id == operation.resource_id
                and balance.owner_id == operation.owner_id
            ),
            None,
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

        if operation.amount <= 0:
            return

        source_balance = next(
            (
                balance
                for balance in world.resource_balances.values()
                if balance.resource_id == operation.resource_id
                and balance.owner_id == operation.source_id
            ),
            None,
        )

        if source_balance is None:
            return

        if source_balance.amount < operation.amount:
            return

        target_balance = next(
            (
                balance
                for balance in world.resource_balances.values()
                if balance.resource_id == operation.resource_id
                and balance.owner_id == operation.target_id
            ),
            None,
        )

        if target_balance is None:
            balance_id = (
                max(world.resource_balances.keys(), default=0) + 1
            )

            target_balance = ResourceBalance(
                id=balance_id,
                resource_id=operation.resource_id,
                owner_id=operation.target_id,
                amount=0,
            )

            world.resource_balances[balance_id] = target_balance

        source_balance.amount -= operation.amount
        target_balance.amount += operation.amount

    # ---------------------------------------------------------
    # RELATIONS
    # ---------------------------------------------------------

    def _apply_create_relation(
        self,
        world: WorldState,
        operation: CreateRelationOperation,
    ) -> None:

        if operation.relation_id in world.relations:
            return

        if not operation.relation_type:
            return

        try:
            subject_id = int(operation.subject_id)
            target_id = int(operation.target_id)
        except (TypeError, ValueError):
            return

        if subject_id not in world.entities:
            return

        if target_id not in world.entities:
            return

        relation = Relation(
            id=operation.relation_id,
            subject_id=subject_id,       # ← INT
            relation_type=operation.relation_type,
            target_id=target_id,         # ← INT
            metadata=operation.metadata,
            active=True,
        )

        world.relations[operation.relation_id] = relation


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

            try:
                target_id = int(operation.target_id)
            except (TypeError, ValueError):
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

    def _apply_create_event(
        self,
        world: WorldState,
        operation: CreateEventOperation,
    ) -> None:

        # ID obligatorio
        if not operation.event_id:
            return

        # Tipo obligatorio
        if not operation.event_type:
            return

        # Título obligatorio
        if not operation.title:
            return

        # No sobrescribir
        if operation.event_id in world.events:
            return

        event = Event(
            id=operation.event_id,
            event_type=operation.event_type,
            title=operation.title,
            description=operation.description,
            consequences=operation.consequences,
            session_id=operation.session_id,
            secret=operation.secret,
            metadata=operation.metadata or {},
        )

        world.events[operation.event_id] = event