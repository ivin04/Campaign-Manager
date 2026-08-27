from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from models.world_state import WorldState
from services.world_serializer import WorldSerializer


class MemorySearchService:
    """
    Servicio de acceso estructurado a la memoria del Campaign Manager.

    Responsabilidades:
    - Buscar información candidata dentro del WorldState.
    - Exportar una representación pública estructurada.
    - No modificar el WorldState.
    - No acceder directamente a SQLite.
    - No conocer tablas legacy.
    - No exponer entidades inactivas.
    - No exponer eventos secretos.

    WorldState es la única fuente de verdad.

    La selección, priorización y construcción del contexto textual
    para el LLM pertenecen a ContextBuilder.
    """

    # ============================================================
    # SEARCH
    # ============================================================

    def search(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Busca candidatos que coinciden con una consulta dentro del WorldState.

        No decide la prioridad final ni construye contexto para el LLM.
        La respuesta utiliza exclusivamente las categorías actuales
        del WorldState.
        """

        self._validate_world(world)
        query = self._validate_query(query)

        if not query:
            return self._empty_result()

        needle = query.casefold()

        return {
            "entities": [
                WorldSerializer.entity_to_dict(entity)
                for entity in world.entities.values()
                if getattr(entity, "active", True)
                and self._matches_entity(entity, needle)
            ],

            "items": [
                WorldSerializer.item_to_dict(item)
                for item in world.items.values()
                if self._matches_item(item, needle)
            ],

            "item_instances": [
                WorldSerializer.item_instance_to_dict(instance)
                for instance in world.item_instances.values()
                if self._matches_item_instance(instance, needle)
            ],

            "resources": [
                WorldSerializer.resource_to_dict(resource)
                for resource in world.resources.values()
                if self._matches_resource(resource, needle)
            ],

            "resource_balances": [
                WorldSerializer.resource_balance_to_dict(balance)
                for balance in world.resource_balances.values()
                if self._matches_resource_balance(balance, needle)
            ],

            "relations": [
                WorldSerializer.relation_to_dict(relation)
                for relation in world.relations.values()
                if getattr(relation, "active", True)
                and self._matches_relation(relation, needle)
            ],

            "events": [
                WorldSerializer.event_to_dict(event)
                for event in world.events.values()
                if not getattr(event, "secret", False)
                and self._matches_event(event, needle)
            ],
        }

    # ============================================================
    # EXPORT
    # ============================================================

    def export(
        self,
        world: WorldState,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Exporta la memoria pública completa del WorldState.

        A diferencia de search(), no necesita una consulta.

        Nunca exporta:
        - entidades inactivas
        - relaciones inactivas
        - eventos secretos
        """

        self._validate_world(world)

        return {
            "entities": [
                WorldSerializer.entity_to_dict(entity)
                for entity in world.entities.values()
                if getattr(entity, "active", True)
            ],

            "items": [
                WorldSerializer.item_to_dict(item)
                for item in world.items.values()
            ],

            "item_instances": [
                WorldSerializer.item_instance_to_dict(instance)
                for instance in world.item_instances.values()
            ],

            "resources": [
                WorldSerializer.resource_to_dict(resource)
                for resource in world.resources.values()
            ],

            "resource_balances": [
                WorldSerializer.resource_balance_to_dict(balance)
                for balance in world.resource_balances.values()
            ],

            "relations": [
                WorldSerializer.relation_to_dict(relation)
                for relation in world.relations.values()
                if getattr(relation, "active", True)
            ],

            "events": [
                WorldSerializer.event_to_dict(event)
                for event in world.events.values()
                if not getattr(event, "secret", False)
            ],
        }

    # ============================================================
    # MATCHING
    # ============================================================

    @staticmethod
    def _matches_entity(
        entity: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(entity, "id", None),
            getattr(entity, "name", None),
            getattr(entity, "entity_type", None),
            getattr(entity, "description", None),
            getattr(entity, "notes", None),
        )

    @staticmethod
    def _matches_item(
        item: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(item, "id", None),
            getattr(item, "name", None),
            getattr(item, "description", None),
            getattr(item, "significance", None),
            getattr(item, "notes", None),
        )

    @staticmethod
    def _matches_item_instance(
        instance: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(instance, "id", None),
            getattr(instance, "item_id", None),
            getattr(instance, "owner_id", None),
            getattr(instance, "location_id", None),
            getattr(instance, "notes", None),
            getattr(instance, "metadata", None),
        )

    @staticmethod
    def _matches_resource(
        resource: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(resource, "id", None),
            getattr(resource, "name", None),
            getattr(resource, "resource_type", None),
            getattr(resource, "unit", None),
            getattr(resource, "notes", None),
        )

    @staticmethod
    def _matches_resource_balance(
        balance: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(balance, "id", None),
            getattr(balance, "resource_id", None),
            getattr(balance, "owner_id", None),
            getattr(balance, "amount", None),
            getattr(balance, "notes", None),
            getattr(balance, "metadata", None),
        )

    @staticmethod
    def _matches_relation(
        relation: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(relation, "id", None),
            getattr(relation, "subject_id", None),
            getattr(relation, "target_id", None),
            getattr(relation, "relation_type", None),
            getattr(relation, "description", None),
            getattr(relation, "notes", None),
            getattr(relation, "metadata", None),
        )

    @staticmethod
    def _matches_event(
        event: Any,
        needle: str,
    ) -> bool:
        return MemorySearchService._matches(
            needle,
            getattr(event, "id", None),
            getattr(event, "event_type", None),
            getattr(event, "title", None),
            getattr(event, "description", None),
            getattr(event, "consequences", None),
            getattr(event, "session_id", None),
            getattr(event, "metadata", None),
        )

    @staticmethod
    def _matches(
        needle: str,
        *values: Any,
    ) -> bool:
        """
        Busca needle dentro de valores escalares o estructuras
        de metadata.
        """

        for value in values:
            if value is None:
                continue

            if isinstance(value, dict):
                value = " ".join(
                    f"{key} {val}"
                    for key, val in value.items()
                )

            elif isinstance(value, (list, tuple, set)):
                value = " ".join(str(item) for item in value)

            if needle in str(value).casefold():
                return True

        return False

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate_world(world: WorldState) -> None:
        if not isinstance(world, WorldState):
            raise TypeError("world must be a WorldState.")

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("query must be a string.")

        return query.strip()

    # ============================================================
    # EMPTY RESULT
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