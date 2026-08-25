from models.extraction import ExtractedFact
from models.entity import Entity
from models.item import Item, ItemInstance
from models.resource import Resource, ResourceBalance
from models.relation import Relation

from operations.world_operations import (
    TransferItemOperation,
    GainResourceOperation,
    SpendResourceOperation,
    TransferResourceOperation,
    CreateRelationOperation,
    UpdateRelationOperation,
    RemoveRelationOperation,
)

from services.entity_resolution import EntityResolver
from services.item_resolution import ItemResolver

from typing import Union

import math

WorldOperation = Union[
    TransferItemOperation,
    GainResourceOperation,
    SpendResourceOperation,
    TransferResourceOperation,
    CreateRelationOperation,
    UpdateRelationOperation,
    RemoveRelationOperation,
]

class WorldResolver:

    def __init__(
        self,
        entities: dict[int, Entity],
        items: dict[int, Item],
        item_instances: dict[int, ItemInstance],
        resources: dict[int, Resource],
        resource_balances: dict[int, ResourceBalance],
        relations: dict[str, Relation],
    ):
        self.entity_resolver = EntityResolver(entities)

        self.item_resolver = ItemResolver(
            items,
            item_instances,
        )

        self.resources = resources
        self.resource_balances = resource_balances
        self.relations = relations

    def resolve(
        self,
        facts: list[ExtractedFact],
    ) -> list[WorldOperation]:

        operations = []

        for fact in facts:

            if fact.fact_type == "ITEM_TRANSFERRED":
                operation = self._resolve_item_transfer(fact)

            elif fact.fact_type == "RESOURCE_GAINED":
                operation = self._resolve_resource_gained(fact)

            elif fact.fact_type == "RESOURCE_SPENT":
                operation = self._resolve_resource_spent(fact)

            elif fact.fact_type == "RESOURCE_TRANSFERRED":
                operation = self._resolve_resource_transferred(fact)

            elif fact.fact_type == "RELATION_CREATED":
                operation = self._resolve_relation_created(fact)

            elif fact.fact_type == "RELATION_CHANGED":
                operation = self._resolve_relation_changed(fact)

            elif fact.fact_type == "RELATION_REMOVED":
                operation = self._resolve_relation_removed(fact)

            else:
                operation = None

            if operation is not None:
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

        if not math.isfinite(amount):
            return None

        if amount <= 0:
            return None

        resource = self._find_resource(resource_name)

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

        if not math.isfinite(amount):
            return None

        if amount <= 0:
            return None

        resource = self._find_resource(resource_name)

        if not resource:
            return None

        owner = self.entity_resolver.find(
            owner_name
        )

        if not owner:
            return None

        balance = self._find_balance(
            resource.id,
            owner.id,
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

        if not math.isfinite(amount):
            return None

        if amount <= 0:
            return None

        resource = self._find_resource(resource_name)

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

        if source.id == target.id:
            return None

        balance = self._find_balance(
            resource.id,
            source.id,
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

    def _resolve_relation_created(
        self,
        fact: ExtractedFact,
    ) -> CreateRelationOperation | None:

        relation_id = fact.data.get("relation_id", "")
        subject_name = fact.data.get("subject", "")
        relation_type = fact.data.get("relation_type", "")
        target_name = fact.data.get("target", "")
        metadata = fact.data.get("metadata")

        if not isinstance(relation_id, str):
            return None

        if not relation_id.strip():
            return None

        if not isinstance(subject_name, str):
            return None

        if not subject_name.strip():
            return None

        if not isinstance(relation_type, str):
            return None

        if not relation_type.strip():
            return None

        if not isinstance(target_name, str):
            return None

        if not target_name.strip():
            return None

        subject = self.entity_resolver.find(
            subject_name
        )

        if not subject:
            return None

        target = self.entity_resolver.find(
            target_name
        )

        if not target:
            return None

        if metadata is not None and not isinstance(metadata, dict):
            return None

        return CreateRelationOperation(
            relation_id=relation_id,
            subject_id=subject.id,
            relation_type=relation_type,
            target_id=target.id,
            metadata=metadata,
        )

    def _resolve_relation_changed(
        self,
        fact: ExtractedFact,
    ) -> UpdateRelationOperation | None:

        relation_id = fact.data.get("relation_id", "")
        relation_type = fact.data.get("relation_type")
        target_id = fact.data.get("target_id")
        metadata = fact.data.get("metadata")
        active = fact.data.get("active")

        if not isinstance(relation_id, str):
            return None

        if not relation_id.strip():
            return None

        # Tiene que existir al menos un cambio
        if (
            relation_type is None
            and target_id is None
            and metadata is None
            and active is None
        ):
            return None

        # relation_type
        if relation_type is not None:
            if not isinstance(relation_type, str):
                return None

            if not relation_type.strip():
                return None

        # target_id
        if target_id is not None:

            if isinstance(target_id, bool):
                return None

            try:
                target_id = int(target_id)
            except (TypeError, ValueError):
                return None

        # metadata
        if metadata is not None and not isinstance(metadata, dict):
            return None

        # active
        if active is not None and not isinstance(active, bool):
            return None

        return UpdateRelationOperation(
            relation_id=relation_id,
            relation_type=relation_type,
            target_id=target_id,
            metadata=metadata,
            active=active,
        )

    def _resolve_relation_removed(
        self,
        fact: ExtractedFact,
    ) -> RemoveRelationOperation | None:

        relation_id = fact.data.get("relation_id", "")

        if not isinstance(relation_id, str):
            return None

        if not relation_id.strip():
            return None

        return RemoveRelationOperation(
            relation_id=relation_id,
        )

    def _find_resource(
        self,
        resource_name: str,
    ) -> Resource | None:

        normalized_name = resource_name.strip().casefold()

        if not normalized_name:
            return None

        return next(
            (
                resource
                for resource in self.resources.values()
                if resource.name.strip().casefold()
                == normalized_name
            ),
            None,
        )

    def _find_balance(
        self,
        resource_id: int,
        owner_id: int,
    ) -> ResourceBalance | None:

        balances = [
            balance
            for balance in self.resource_balances.values()
            if balance.resource_id == resource_id
            and balance.owner_id == owner_id
        ]

        if len(balances) != 1:
            return None

        return balances[0]