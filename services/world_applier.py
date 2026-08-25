from models.world_state import WorldState

from operations.world_operations import (
    TransferItemOperation,
    GainResourceOperation,
    SpendResourceOperation,
    TransferResourceOperation,
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

        if not balance:
            return

        balance.amount += operation.amount

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

        if not balance:
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

        if not source_balance:
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

        if not target_balance:
            return

        source_balance.amount -= operation.amount
        target_balance.amount += operation.amount