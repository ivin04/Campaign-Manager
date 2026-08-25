from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from models.world_state import WorldState


class MemorySearchService:
    """
    Servicio único de memoria del Campaign Manager.

    Responsabilidades:
    - Buscar información relevante dentro del WorldState.
    - Generar contexto textual para SillyTavern.
    - Exportar memoria pública.
    - No modificar el WorldState.
    - No acceder directamente a SQLite.
    - No conocer tablas legacy.
    - No exponer entidades inactivas.
    - No exponer eventos secretos.

    WorldState es la única fuente de verdad.
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
        Busca información relevante dentro del WorldState.

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
                self._entity_to_dict(entity)
                for entity in world.entities.values()
                if getattr(entity, "active", True)
                and self._matches_entity(entity, needle)
            ],

            "items": [
                self._item_to_dict(item)
                for item in world.items.values()
                if self._matches_item(item, needle)
            ],

            "item_instances": [
                self._item_instance_to_dict(instance)
                for instance in world.item_instances.values()
                if self._matches_item_instance(instance, needle)
            ],

            "resources": [
                self._resource_to_dict(resource)
                for resource in world.resources.values()
                if self._matches_resource(resource, needle)
            ],

            "resource_balances": [
                self._resource_balance_to_dict(balance)
                for balance in world.resource_balances.values()
                if self._matches_resource_balance(balance, needle)
            ],

            "relations": [
                self._relation_to_dict(relation)
                for relation in world.relations.values()
                if getattr(relation, "active", True)
                and self._matches_relation(relation, needle)
            ],

            "events": [
                self._event_to_dict(event)
                for event in world.events.values()
                if not getattr(event, "secret", False)
                and self._matches_event(event, needle)
            ],
        }

    # ============================================================
    # CONTEXT
    # ============================================================

    def context(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, Any]:
        """
        Genera contexto de memoria para consumo externo.

        Devuelve:
            {
                "query": "...",
                "results": {...},
                "context": "..."
            }

        `results` mantiene el resultado estructurado de search().
        `context` es la representación textual preparada para
        SillyTavern.
        """

        self._validate_world(world)

        normalized_query = self._validate_query(query)

        results = self.search(world, normalized_query)

        return {
            "query": normalized_query,
            "results": results,
            "context": self._build_context(results),
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
                self._entity_to_dict(entity)
                for entity in world.entities.values()
                if getattr(entity, "active", True)
            ],

            "items": [
                self._item_to_dict(item)
                for item in world.items.values()
            ],

            "item_instances": [
                self._item_instance_to_dict(instance)
                for instance in world.item_instances.values()
            ],

            "resources": [
                self._resource_to_dict(resource)
                for resource in world.resources.values()
            ],

            "resource_balances": [
                self._resource_balance_to_dict(balance)
                for balance in world.resource_balances.values()
            ],

            "relations": [
                self._relation_to_dict(relation)
                for relation in world.relations.values()
                if getattr(relation, "active", True)
            ],

            "events": [
                self._event_to_dict(event)
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
            getattr(relation, "source_id", None),
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
    # CONTEXT BUILDING
    # ============================================================

    @staticmethod
    def _build_context(
        results: dict[str, list[dict[str, Any]]],
    ) -> str:
        """
        Convierte resultados estructurados en contexto legible
        para SillyTavern.

        Solo se incluyen categorías que tengan resultados.
        """

        sections: list[str] = [
            "MEMORIA DE CAMPAÑA RELEVANTE:"
        ]

        MemorySearchService._append_entities(
            sections,
            results.get("entities", []),
        )

        MemorySearchService._append_items(
            sections,
            results.get("items", []),
        )

        MemorySearchService._append_item_instances(
            sections,
            results.get("item_instances", []),
        )

        MemorySearchService._append_resources(
            sections,
            results.get("resources", []),
        )

        MemorySearchService._append_resource_balances(
            sections,
            results.get("resource_balances", []),
        )

        MemorySearchService._append_relations(
            sections,
            results.get("relations", []),
        )

        MemorySearchService._append_events(
            sections,
            results.get("events", []),
        )

        if len(sections) == 1:
            sections.append("Sin información relevante.")

        return "\n".join(sections)

    @staticmethod
    def _append_entities(
        sections: list[str],
        entities: list[dict[str, Any]],
    ) -> None:
        if not entities:
            return

        sections.append("[ENTITIES]")

        for entity in entities:
            name = entity.get("name", "Sin nombre")
            entity_type = entity.get("entity_type", "unknown")
            description = entity.get("description", "")
            notes = entity.get("notes", "")

            line = f"- {name} ({entity_type})"

            if description:
                line += f": {description}"

            if notes:
                line += f" Notas: {notes}"

            sections.append(line)

    @staticmethod
    def _append_items(
        sections: list[str],
        items: list[dict[str, Any]],
    ) -> None:
        if not items:
            return

        sections.append("[ITEMS]")

        for item in items:
            name = item.get("name", "Sin nombre")
            description = item.get("description", "")
            significance = item.get("significance", "")
            notes = item.get("notes", "")

            line = f"- {name}"

            if description:
                line += f": {description}"

            if significance:
                line += f" Importancia: {significance}"

            if notes:
                line += f" Notas: {notes}"

            sections.append(line)

    @staticmethod
    def _append_item_instances(
        sections: list[str],
        instances: list[dict[str, Any]],
    ) -> None:
        if not instances:
            return

        sections.append("[ITEM_INSTANCES]")

        for instance in instances:
            instance_id = instance.get("id", "unknown")
            item_id = instance.get("item_id")
            owner_id = instance.get("owner_id")
            location_id = instance.get("location_id")

            line = f"- Instancia {instance_id}"

            if item_id is not None:
                line += f" item={item_id}"

            if owner_id is not None:
                line += f" propietario={owner_id}"

            if location_id is not None:
                line += f" ubicación={location_id}"

            sections.append(line)

    @staticmethod
    def _append_resources(
        sections: list[str],
        resources: list[dict[str, Any]],
    ) -> None:
        if not resources:
            return

        sections.append("[RESOURCES]")

        for resource in resources:
            name = resource.get("name", "Sin nombre")
            resource_type = resource.get("resource_type", "")
            unit = resource.get("unit", "")
            notes = resource.get("notes", "")

            line = f"- {name}"

            if resource_type:
                line += f" ({resource_type})"

            if unit:
                line += f" Unidad: {unit}"

            if notes:
                line += f" Notas: {notes}"

            sections.append(line)

    @staticmethod
    def _append_resource_balances(
        sections: list[str],
        balances: list[dict[str, Any]],
    ) -> None:
        if not balances:
            return

        sections.append("[RESOURCE_BALANCES]")

        for balance in balances:
            balance_id = balance.get("id", "unknown")
            resource_id = balance.get("resource_id")
            owner_id = balance.get("owner_id")
            amount = balance.get("amount")

            line = f"- Balance {balance_id}"

            if resource_id is not None:
                line += f" recurso={resource_id}"

            if owner_id is not None:
                line += f" propietario={owner_id}"

            if amount is not None:
                line += f" cantidad={amount}"

            sections.append(line)

    @staticmethod
    def _append_relations(
        sections: list[str],
        relations: list[dict[str, Any]],
    ) -> None:
        if not relations:
            return

        sections.append("[RELATIONS]")

        for relation in relations:
            relation_type = relation.get(
                "relation_type",
                "unknown",
            )

            source_id = relation.get("source_id")
            target_id = relation.get("target_id")

            line = f"- {relation_type}"

            if source_id is not None:
                line += f": {source_id}"

            if target_id is not None:
                line += f" -> {target_id}"

            description = relation.get("description")
            if description:
                line += f" {description}"

            sections.append(line)

    @staticmethod
    def _append_events(
        sections: list[str],
        events: list[dict[str, Any]],
    ) -> None:
        if not events:
            return

        sections.append("[EVENTS]")

        for event in events:
            title = event.get("title", "Sin título")
            description = event.get("description", "")
            consequences = event.get("consequences", "")

            line = f"- {title}"

            if description:
                line += f": {description}"

            if consequences:
                line += f" Consecuencias: {consequences}"

            sections.append(line)

    # ============================================================
    # SERIALIZATION
    # ============================================================

    @staticmethod
    def _serialize(value: Any) -> dict[str, Any]:
        """
        Serialización defensiva de objetos del dominio.
        """

        if is_dataclass(value):
            return asdict(value)

        if isinstance(value, dict):
            return dict(value)

        if hasattr(value, "__dict__"):
            return dict(value.__dict__)

        raise TypeError(
            f"Cannot serialize value of type {type(value).__name__}."
        )

    @classmethod
    def _entity_to_dict(cls, entity: Any) -> dict[str, Any]:
        return cls._serialize(entity)

    @classmethod
    def _item_to_dict(cls, item: Any) -> dict[str, Any]:
        return cls._serialize(item)

    @classmethod
    def _item_instance_to_dict(
        cls,
        instance: Any,
    ) -> dict[str, Any]:
        return cls._serialize(instance)

    @classmethod
    def _resource_to_dict(
        cls,
        resource: Any,
    ) -> dict[str, Any]:
        return cls._serialize(resource)

    @classmethod
    def _resource_balance_to_dict(
        cls,
        balance: Any,
    ) -> dict[str, Any]:
        return cls._serialize(balance)

    @classmethod
    def _relation_to_dict(
        cls,
        relation: Any,
    ) -> dict[str, Any]:
        return cls._serialize(relation)

    @classmethod
    def _event_to_dict(
        cls,
        event: Any,
    ) -> dict[str, Any]:
        return cls._serialize(event)

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