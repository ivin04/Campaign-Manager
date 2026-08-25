from __future__ import annotations

from dataclasses import asdict
from typing import Any

from models.world_state import WorldState


class MemorySearchService:
    """
    Servicio de búsqueda de memoria sobre WorldState.

    El WorldState es la única fuente de verdad.

    Este servicio:
    - no modifica el WorldState;
    - no accede a SQLite;
    - no conoce tablas legacy;
    - no expone entidades inactivas;
    - no expone eventos secretos;
    - prepara contexto textual para SillyTavern.
    """

    MEMORY_CATEGORIES = (
        "entities",
        "items",
        "resources",
        "relations",
        "events",
    )

    def search(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, list[dict[str, Any]]]:

        if not isinstance(world, WorldState):
            raise TypeError("world must be a WorldState.")

        if not isinstance(query, str):
            raise TypeError("query must be a string.")

        query = query.strip()

        if not query:
            return self._empty_result()

        needle = query.casefold()

        return {
            "entities": [
                self._entity_to_dict(entity)
                for entity in world.entities.values()
                if entity.active
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
                if instance.active
                and self._matches_item_instance(instance, needle)
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
                if self._matches_relation(relation, needle)
            ],
            "events": [
                self._event_to_dict(event)
                for event in world.events.values()
                if not event.secret
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

        result = self.search(world, query)

        return {
            "query": query.strip(),
            "results": result,
            "context": self._format_context(result),
        }

    @staticmethod
    def _format_context(
        result: dict[str, list[dict[str, Any]]],
    ) -> str:

        sections = []

        labels = {
            "entities": "ENTITIES",
            "items": "ITEMS",
            "item_instances": "ITEM INSTANCES",
            "resources": "RESOURCES",
            "resource_balances": "RESOURCE BALANCES",
            "relations": "RELATIONS",
            "events": "EVENTS",
        }

        for category, label in labels.items():

            entries = result.get(category, [])

            if not entries:
                continue

            lines = [f"[{label}]"]

            for entry in entries:
                if category == "entities":
                    lines.append(
                        f"- {entry.get('name', '')}"
                        f" ({entry.get('entity_type', '')}): "
                        f"{entry.get('description', '')}"
                        + (
                            f" Notas: {entry['notes']}"
                            if entry.get("notes")
                            else ""
                        )
                    )

                elif category == "items":
                    lines.append(
                        f"- {entry.get('name', '')}: "
                        f"{entry.get('description', '')}"
                        + (
                            f" Importancia: {entry['significance']}"
                            if entry.get("significance")
                            else ""
                        )
                    )

                elif category == "events":
                    lines.append(
                        f"- {entry.get('title', '')}: "
                        f"{entry.get('description', '')}"
                    )

                else:
                    lines.append(f"- {entry}")

            sections.append("\n".join(lines))

        if not sections:
            return "MEMORIA DE CAMPAÑA RELEVANTE:\n- No se encontró información relevante."

        return "MEMORIA DE CAMPAÑA RELEVANTE:\n" + "\n\n".join(sections)

    def _build_context(
        self,
        results: dict[str, list[dict[str, Any]]],
    ) -> str:
        """
        Convierte los resultados estructurados en contexto legible
        para el modelo narrativo.
        """

        sections: list[str] = [
            "MEMORIA DE CAMPAÑA RELEVANTE:"
        ]

        found_any = False

        # --------------------------------------------------------
        # ENTIDADES
        # --------------------------------------------------------

        for entity in results["entities"]:
            found_any = True

            name = entity.get("name", "Entidad desconocida")
            entity_type = entity.get("entity_type", "")
            description = entity.get("description", "")
            notes = entity.get("notes", "")

            line = f"- {name}"

            if entity_type:
                line += f" ({entity_type})"

            if description:
                line += f": {description}"

            if notes:
                line += f" Notas: {notes}"

            sections.append(line)

        # --------------------------------------------------------
        # ITEMS
        # --------------------------------------------------------

        for item in results["items"]:
            found_any = True

            name = item.get("name", "Objeto desconocido")
            description = item.get("description", "")
            significance = item.get("significance", "")
            notes = item.get("notes", "")

            line = f"- Objeto: {name}"

            if description:
                line += f": {description}"

            if significance:
                line += f" Importancia: {significance}"

            if notes:
                line += f" Notas: {notes}"

            sections.append(line)

        # --------------------------------------------------------
        # RESOURCES
        # --------------------------------------------------------

        for resource in results["resources"]:
            found_any = True

            name = resource.get("name", "Recurso desconocido")
            resource_type = resource.get("resource_type", "")
            unit = resource.get("unit", "")
            notes = resource.get("notes", "")

            line = f"- Recurso: {name}"

            if resource_type:
                line += f" ({resource_type})"

            if unit:
                line += f" Unidad: {unit}"

            if notes:
                line += f" Notas: {notes}"

            sections.append(line)

        # --------------------------------------------------------
        # RELATIONS
        # --------------------------------------------------------

        for relation in results["relations"]:
            found_any = True

            relation_id = relation.get("id", "")
            subject_id = relation.get("subject_id", "")
            relation_type = relation.get("relation_type", "")
            target_id = relation.get("target_id", "")
            metadata = relation.get("metadata")

            line = (
                f"- Relación {relation_id}: "
                f"{subject_id} --{relation_type}--> {target_id}"
            )

            if metadata:
                line += f" Metadata: {metadata}"

            sections.append(line)

        # --------------------------------------------------------
        # EVENTS
        # --------------------------------------------------------

        for event in results["events"]:
            found_any = True

            title = event.get("title", "Evento")
            description = event.get("description", "")
            consequences = event.get("consequences", "")

            line = f"- Evento: {title}"

            if description:
                line += f": {description}"

            if consequences:
                line += f" Consecuencias: {consequences}"

            sections.append(line)

        if not found_any:
            sections.append("- No se encontró memoria relevante.")

        return "\n".join(sections)

    # ============================================================
    # MATCHING
    # ============================================================

    @staticmethod
    def _matches_entity(entity: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            entity.name,
            entity.entity_type,
            entity.description,
            entity.notes,
        )

    @staticmethod
    def _matches_item(item: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            item.name,
            item.description,
            item.significance,
            item.notes,
        )

    @staticmethod
    def _matches_item_instance(instance: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            instance.id,
            instance.item_id,
            instance.instance_number,
            instance.owner_id,
            instance.location_id,
            instance.condition,
            instance.notes,
        )


    @staticmethod
    def _matches_resource_balance(balance: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            balance.id,
            balance.resource_id,
            balance.owner_id,
            balance.amount,
            balance.notes,
        )

    @staticmethod
    def _matches_resource(resource: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            resource.name,
            resource.resource_type,
            resource.unit,
            resource.notes,
        )

    @staticmethod
    def _matches_relation(relation: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            relation.id,
            relation.subject_id,
            relation.relation_type,
            relation.target_id,
            getattr(relation, "metadata", None),
        )

    @staticmethod
    def _matches_event(event: Any, needle: str) -> bool:
        return MemorySearchService._matches(
            needle,
            event.id,
            event.event_type,
            event.title,
            event.description,
            event.consequences,
            event.session_id,
            getattr(event, "metadata", None),
        )

    @staticmethod
    def _matches(needle: str, *values: Any) -> bool:
        for value in values:
            if value is None:
                continue

            if isinstance(value, (dict, list, tuple, set)):
                value = str(value)

            if needle in str(value).casefold():
                return True

        return False

    # ============================================================
    # SERIALIZATION
    # ============================================================

    @staticmethod
    def _entity_to_dict(entity: Any) -> dict[str, Any]:
        return asdict(entity)

    @staticmethod
    def _item_to_dict(item: Any) -> dict[str, Any]:
        return asdict(item)

    @staticmethod
    def _item_instance_to_dict(instance: Any) -> dict[str, Any]:
        return asdict(instance)


    @staticmethod
    def _resource_balance_to_dict(balance: Any) -> dict[str, Any]:
        return asdict(balance)

    @staticmethod
    def _resource_to_dict(resource: Any) -> dict[str, Any]:
        return asdict(resource)

    @staticmethod
    def _relation_to_dict(relation: Any) -> dict[str, Any]:
        return asdict(relation)

    @staticmethod
    def _event_to_dict(event: Any) -> dict[str, Any]:
        return asdict(event)

    # ============================================================
    # EMPTY
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