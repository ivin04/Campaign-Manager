from models.world_state import WorldState
from operations.world_operations import TransferItemOperation


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

        instance.owner_id = operation.new_owner_id