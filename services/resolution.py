from models.extraction import ExtractedFact
from models.entity import Entity
from models.item import Item, ItemInstance
from models.resource import Resource, ResourceBalance

from operations.world_operations import (
    TransferItemOperation,
    GainResourceOperation,
    SpendResourceOperation,
    TransferResourceOperation,
)

from services.entity_resolution import EntityResolver
from services.item_resolution import ItemResolver


class WorldResolver:

    def __init__(
        self,
        entities: dict[int, Entity],
        items: dict[int, Item],
        item_instances: dict[int, ItemInstance],
        resources: dict[int, Resource],
        resource_balances: dict[int, ResourceBalance],
    ):
        self.entity_resolver = EntityResolver(entities)

        self.item_resolver = ItemResolver(
            items,
            item_instances,
        )

        self.resources = resources
        self.resource_balances = resource_balances

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

            if fact.fact_type == "RESOURCE_GAINED":

                operation = self._resolve_resource_gained(
                    fact
                )

                if operation:
                    operations.append(operation)

            if fact.fact_type == "RESOURCE_SPENT":

                operation = self._resolve_resource_spent(
                    fact
                )

                if operation:
                    operations.append(operation)

            if fact.fact_type == "RESOURCE_TRANSFERRED":

                operation = self._resolve_resource_transferred(
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

    def _resolve_resource_gained(
        self,
        fact: ExtractedFact,
    ) -> GainResourceOperation | None:

        resource_name = fact.data.get("resource", "")
        owner_name = fact.data.get("owner", "")
        amount = fact.data.get("amount")

        if not resource_name:
            return None

        if not owner_name:
            return None

        if amount is None:
            return None

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return None

        if amount <= 0:
            return None

        resource = next(
            (
                resource
                for resource in self.resources.values()
                if resource.name.casefold()
                == resource_name.casefold()
            ),
            None,
        )

        if not resource:
            return None

        owner = self.entity_resolver.find(owner_name)

        if not owner:
            return None

        return GainResourceOperation(
            resource_id=resource.id,
            owner_id=owner.id,
            amount=amount,
        )

    def _resolve_resource_spent(
        self,
        fact: ExtractedFact,
    ) -> SpendResourceOperation | None:

        resource_name = fact.data.get("resource", "")
        owner_name = fact.data.get("owner", "")
        amount = fact.data.get("amount")

        if not resource_name:
            return None

        if not owner_name:
            return None

        if amount is None:
            return None

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return None

        if amount <= 0:
            return None

        resource = next(
            (
                resource
                for resource in self.resources.values()
                if resource.name.casefold()
                == resource_name.casefold()
            ),
            None,
        )

        if not resource:
            return None

        owner = self.entity_resolver.find(
            owner_name
        )

        if not owner:
            return None

        balance = next(
            (
                balance
                for balance in self.resource_balances.values()
                if balance.resource_id == resource.id
                and balance.owner_id == owner.id
            ),
            None,
        )

        if not balance:
            return None

        if balance.amount < amount:
            return None

        return SpendResourceOperation(
            resource_id=resource.id,
            owner_id=owner.id,
            amount=amount,
        )

    def _resolve_resource_transferred(
        self,
        fact: ExtractedFact,
    ) -> TransferResourceOperation | None:

        resource_name = fact.data.get("resource", "")
        source_name = fact.data.get("from", "")
        target_name = fact.data.get("to", "")
        amount = fact.data.get("amount")

        if not resource_name:
            return None

        if not source_name:
            return None

        if not target_name:
            return None

        if amount is None:
            return None

        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return None

        if amount <= 0:
            return None

        resource = next(
            (
                resource
                for resource in self.resources.values()
                if resource.name.casefold()
                == resource_name.casefold()
            ),
            None,
        )

        if not resource:
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

        balance = next(
            (
                balance
                for balance in self.resource_balances.values()
                if balance.resource_id == resource.id
                and balance.owner_id == source.id
            ),
            None,
        )

        if not balance:
            return None

        if balance.amount < amount:
            return None

        return TransferResourceOperation(
            resource_id=resource.id,
            source_id=source.id,
            target_id=target.id,
            amount=amount,
        )