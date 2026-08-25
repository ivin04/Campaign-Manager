from models.extraction import ExtractedFact
from models.entity import Entity
from models.item import Item, ItemInstance

from operations.world_operations import TransferItemOperation

from services.entity_resolution import EntityResolver
from services.item_resolution import ItemResolver


class WorldResolver:

    def __init__(
        self,
        entities: dict[int, Entity],
        items: dict[int, Item],
        item_instances: dict[int, ItemInstance],
    ):
        self.entity_resolver = EntityResolver(entities)

        self.item_resolver = ItemResolver(
            items,
            item_instances,
        )

    def resolve(
        self,
        facts: list[ExtractedFact],
    ) -> list[object]:

        operations = []

        for fact in facts:

            if fact.fact_type == "ITEM_TRANSFERRED":

                operation = self._resolve_item_transfer(
                    fact
                )

                if operation:
                    operations.append(operation)

        return operations

    def _resolve_item_transfer(
        self,
        fact: ExtractedFact,
    ) -> TransferItemOperation | None:

        item_name = fact.data.get("item", "")
        source_name = fact.data.get("from", "")
        target_name = fact.data.get("to", "")

        if not item_name:
            return None

        if not source_name:
            return None

        if not target_name:
            return None

        item = self.item_resolver.find_item(
            item_name
        )

        if not item:
            return None

        source = self.entity_resolver.find(
            source_name
        )

        if not source:
            return None

        target = self.entity_resolver.find(
            target_name
        )

        if not target:
            return None

        instances = self.item_resolver.find_instances_by_owner(
            item.id,
            source.id,
        )

        if not instances:
            return None

        if len(instances) > 1:
            return None

        instance = instances[0]

        return TransferItemOperation(
            instance_id=instance.id,
            new_owner_id=target.id,
        )