from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from models.world_state import WorldState


class WorldMemoryService:
    """
    Provides read-only memory/context access to the current WorldState.

    This service contains no persistence logic and does not mutate the world.
    WorldService remains the owner of the live WorldState.
    """

    def __init__(self, world_service):
        self.world_service = world_service

    # ============================================================
    # PUBLIC API
    # ============================================================

    def search(self, query: str) -> dict[str, list[dict[str, Any]]]:
        """
        Search public information in the current WorldState.

        Secrets must never be exposed to SillyTavern.
        """

        if not isinstance(query, str) or not query.strip():
            return self._empty_result()

        world = self.world_service.get_world()

        return self._search_world(world, query.strip())

    def context(self, query: str) -> dict[str, Any]:
        """
        Return memory relevant to a query.

        Currently this is based on the same public search result.
        """

        return {
            "query": query,
            "memory": self.search(query),
        }

    def export(self) -> dict[str, Any]:
        """
        Export the public WorldState for external consumers.

        Secrets are removed before returning the data.
        """

        world = self.world_service.get_world()

        return self._serialize_world(world)

    # ============================================================
    # SEARCH
    # ============================================================

    def _search_world(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, list[dict[str, Any]]]:

        query_lower = query.lower()

        result = {
            "entities": [],
            "items": [],
            "item_instances": [],
            "resources": [],
            "resource_balances": [],
            "relations": [],
            "events": [],
        }

        # --------------------------------------------------------
        # Entities
        # --------------------------------------------------------

        for entity in world.entities.values():

            if not entity.active:
                continue

            if self._matches(entity, query_lower):
                result["entities"].append(
                    self._serialize(entity)
                )

        # --------------------------------------------------------
        # Items
        # --------------------------------------------------------

        for item in world.items.values():

            if self._matches(item, query_lower):
                result["items"].append(
                    self._serialize(item)
                )

        # --------------------------------------------------------
        # Item instances
        # --------------------------------------------------------

        for instance in world.item_instances.values():

            if self._matches(instance, query_lower):
                result["item_instances"].append(
                    self._serialize(instance)
                )

        # --------------------------------------------------------
        # Resources
        # --------------------------------------------------------

        for resource in world.resources.values():

            if self._matches(resource, query_lower):
                result["resources"].append(
                    self._serialize(resource)
                )

        # --------------------------------------------------------
        # Resource balances
        # --------------------------------------------------------

        for balance in world.resource_balances.values():

            if self._matches(balance, query_lower):
                result["resource_balances"].append(
                    self._serialize(balance)
                )

        # --------------------------------------------------------
        # Relations
        # --------------------------------------------------------

        for relation in world.relations.values():

            if not relation.active:
                continue

            if self._matches(relation, query_lower):
                result["relations"].append(
                    self._serialize(relation)
                )

        # --------------------------------------------------------
        # Events
        # --------------------------------------------------------

        for event in world.events.values():

            # IMPORTANT:
            # Secret events NEVER leave the application.
            if event.secret:
                continue

            if self._matches(event, query_lower):
                result["events"].append(
                    self._serialize(event)
                )

        return result

    # ============================================================
    # SERIALIZATION
    # ============================================================

    def _serialize_world(
        self,
        world: WorldState,
    ) -> dict[str, Any]:

        return {
            "entities": [
                self._serialize(entity)
                for entity in world.entities.values()
                if entity.active
            ],

            "items": [
                self._serialize(item)
                for item in world.items.values()
            ],

            "item_instances": [
                self._serialize(instance)
                for instance in world.item_instances.values()
                if instance.active
            ],

            "resources": [
                self._serialize(resource)
                for resource in world.resources.values()
            ],

            "resource_balances": [
                self._serialize(balance)
                for balance in world.resource_balances.values()
            ],

            "relations": [
                self._serialize(relation)
                for relation in world.relations.values()
                if relation.active
            ],

            "events": [
                self._serialize(event)
                for event in world.events.values()
                if not event.secret
            ],
        }

    def _serialize(self, value: Any) -> dict[str, Any]:

        if not is_dataclass(value):
            raise TypeError(
                f"Expected dataclass, got {type(value).__name__}"
            )

        data = asdict(value)

        # Defensive security boundary.
        #
        # If a future domain object gains a secrets field,
        # it must not automatically leak through the memory API.
        data.pop("secrets", None)

        return data

    # ============================================================
    # MATCHING
    # ============================================================

    def _matches(
        self,
        value: Any,
        query_lower: str,
    ) -> bool:

        data = self._serialize(value)

        return self._matches_data(data, query_lower)

    def _matches_data(
        self,
        data: dict[str, Any],
        query_lower: str,
    ) -> bool:

        for value in data.values():

            if value is None:
                continue

            if isinstance(value, dict):

                if self._matches_data(value, query_lower):
                    return True

            elif isinstance(value, (list, tuple)):

                for item in value:

                    if query_lower in str(item).lower():
                        return True

            elif query_lower in str(value).lower():

                return True

        return False

    # ============================================================
    # HELPERS
    # ============================================================

    @staticmethod
    def _empty_result() -> dict[str, list[dict[str, Any]]]:

        return {
            "entities": [],
            "items": [],
            "item_instances": [],
            "resources": [],
            "resource_balances": [],
            "relations": [],
            "events": [],
        }