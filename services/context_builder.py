from __future__ import annotations

from typing import Any

from models.world_state import WorldState
from services.memory_search_service import MemorySearchService


class ContextBuilder:
    """
    Construye contexto narrativo relacionado para el LLM.

    MemorySearchService se encarga de encontrar coincidencias.
    ContextBuilder amplía esas coincidencias siguiendo relaciones
    existentes en el WorldState.

    Responsabilidades:

    - Identificar entidades principales.
    - Incluir entidades relacionadas.
    - Incluir relaciones conectadas.
    - Incluir eventos relacionados.
    - Excluir entidades inactivas.
    - Excluir relaciones inactivas.
    - Excluir eventos secretos.
    - No modificar WorldState.
    - No acceder directamente a SQLite.
    """

    DEFAULT_MAX_DEPTH = 1

    def __init__(
        self,
        memory_search_service: MemorySearchService | None = None,
    ) -> None:
        self.memory_search_service = (
            memory_search_service
            or MemorySearchService()
        )

    def build(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, Any]:
        """
        Construye contexto relacionado a partir de una consulta.
        """

        self._validate_world(world)

        normalized_query = self._validate_query(query)

        if not normalized_query:
            return self._empty_result()

        search_result = self.memory_search_service.search(
            world,
            normalized_query,
        )

        entities = self._expand_entities(
            world,
            search_result["entities"],
            max_depth=self.DEFAULT_MAX_DEPTH,
        )

        related_data = self._resolve_related_data(
            world,
            entities,
            search_result,
        )

        relations = self._related_relations(
            world,
            entities,
        )

        events = self._related_events(
            world,
            entities,
        )

        result = {
            "query": normalized_query,
            "entities": entities,
            "items": related_data["items"],
            "item_instances": related_data[
                "item_instances"
            ],
            "resources": related_data["resources"],
            "resource_balances": related_data[
                "resource_balances"
            ],
            "relations": relations,
            "events": events,
        }

        result["context"] = self._build_text_context(
            result
        )

        return result

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate_world(world: WorldState) -> None:
        if not isinstance(world, WorldState):
            raise TypeError(
                "world must be a WorldState"
            )

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise TypeError(
                "query must be a string"
            )

        return query.strip()

    # ============================================================
    # ENTITY EXPANSION
    # ============================================================

    def _expand_entities(
        self,
        world: WorldState,
        matched_entities: list[dict[str, Any]],
        max_depth: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Amplía las entidades encontradas siguiendo relaciones activas
        hasta una profundidad máxima.

        depth 0:
            entidades encontradas directamente por la búsqueda.

        depth 1:
            entidades relacionadas directamente.

        depth 2:
            entidades relacionadas con las anteriores.

        Esto evita recorrer indefinidamente todo el grafo del mundo.
        """

        if max_depth < 0:
            raise ValueError(
                "max_depth must be >= 0"
            )

        entity_depths: dict[int, int] = {}

        for entity in matched_entities:
            entity_id = entity.get("id")

            if isinstance(entity_id, int):
                entity_depths[entity_id] = 0

        for depth in range(max_depth):
            current_ids = {
                entity_id
                for entity_id, entity_depth
                in entity_depths.items()
                if entity_depth == depth
            }

            if not current_ids:
                break

            for relation in world.relations.values():

                if not getattr(
                    relation,
                    "active",
                    True,
                ):
                    continue

                subject_id = getattr(
                    relation,
                    "subject_id",
                    None,
                )

                target_id = getattr(
                    relation,
                    "target_id",
                    None,
                )

                if subject_id in current_ids:
                    if (
                        target_id in world.entities
                        and target_id not in entity_depths
                    ):
                        entity_depths[target_id] = depth + 1

                if target_id in current_ids:
                    if (
                        subject_id in world.entities
                        and subject_id not in entity_depths
                    ):
                        entity_depths[subject_id] = depth + 1

        result: list[dict[str, Any]] = []

        for entity_id in entity_depths:

            entity = world.entities.get(
                entity_id
            )

            if entity is None:
                continue

            if not getattr(
                entity,
                "active",
                True,
            ):
                continue

            result.append(
                self.memory_search_service._entity_to_dict(
                    entity
                )
            )

        result.sort(
            key=lambda entity: (
                entity_depths.get(
                    entity.get("id"),
                    max_depth + 1,
                ),
                entity.get("id", 0),
            )
        )

        return result

    # ============================================================
    # RELATED DATA
    # ============================================================

    def _resolve_related_data(
        self,
        world: WorldState,
        entities: list[dict[str, Any]],
        search_result: dict[str, Any],
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Resuelve datos relacionados con las entidades seleccionadas.

        Amplía el resultado de búsqueda para mantener coherencia
        entre:

            Entity
                ↓
            ItemInstance
                ↓
            Item

        y:

            Entity
                ↓
            ResourceBalance
                ↓
            Resource

        También incluye las instancias cuya localización pertenece
        a una entidad seleccionada.

        No modifica WorldState.
        """

        entity_ids = {
            entity.get("id")
            for entity in entities
            if isinstance(entity.get("id"), int)
        }

        items_by_id = {
            item.get("id"): item
            for item in search_result.get("items", [])
            if isinstance(item.get("id"), int)
        }

        item_instances_by_id = {
            instance.get("id"): instance
            for instance in search_result.get(
                "item_instances",
                [],
            )
            if isinstance(instance.get("id"), int)
        }

        resources_by_id = {
            resource.get("id"): resource
            for resource in search_result.get(
                "resources",
                [],
            )
            if isinstance(resource.get("id"), int)
        }

        resource_balances_by_id = {
            balance.get("id"): balance
            for balance in search_result.get(
                "resource_balances",
                [],
            )
            if isinstance(balance.get("id"), int)
        }

        # --------------------------------------------------------
        # ITEM INSTANCES
        # --------------------------------------------------------

        for instance in world.item_instances.values():

            if not getattr(
                instance,
                "active",
                True,
            ):
                continue

            owner_id = getattr(
                instance,
                "owner_id",
                None,
            )

            location_id = getattr(
                instance,
                "location_id",
                None,
            )

            if (
                owner_id not in entity_ids
                and location_id not in entity_ids
            ):
                continue

            instance_id = getattr(
                instance,
                "id",
                None,
            )

            if instance_id is None:
                continue

            instance_dict = (
                self.memory_search_service
                ._item_instance_to_dict(
                    instance
                )
            )

            item_instances_by_id[
                instance_id
            ] = instance_dict

            # Resolver Item padre
            item_id = getattr(
                instance,
                "item_id",
                None,
            )

            item = world.items.get(
                item_id
            )

            if item is not None:
                item_id = getattr(
                    item,
                    "id",
                    None,
                )

                if item_id is not None:
                    items_by_id[item_id] = (
                        self.memory_search_service
                        ._item_to_dict(item)
                    )

        # --------------------------------------------------------
        # RESOURCE BALANCES
        # --------------------------------------------------------

        for balance in world.resource_balances.values():

            owner_id = getattr(
                balance,
                "owner_id",
                None,
            )

            if owner_id not in entity_ids:
                continue

            balance_id = getattr(
                balance,
                "id",
                None,
            )

            if balance_id is None:
                continue

            balance_dict = (
                self.memory_search_service
                ._resource_balance_to_dict(
                    balance
                )
            )

            resource_balances_by_id[
                balance_id
            ] = balance_dict

            # Resolver Resource padre
            resource_id = getattr(
                balance,
                "resource_id",
                None,
            )

            resource = world.resources.get(
                resource_id
            )

            if resource is not None:
                resource_id = getattr(
                    resource,
                    "id",
                    None,
                )

                if resource_id is not None:
                    resources_by_id[
                        resource_id
                    ] = (
                        self.memory_search_service
                        ._resource_to_dict(
                            resource
                        )
                    )

        # --------------------------------------------------------
        # RESULTADO
        # --------------------------------------------------------

        return {
            "items": list(
                items_by_id.values()
            ),
            "item_instances": list(
                item_instances_by_id.values()
            ),
            "resources": list(
                resources_by_id.values()
            ),
            "resource_balances": list(
                resource_balances_by_id.values()
            ),
        }

    # ============================================================
    # RELATIONS
    # ============================================================

    @staticmethod
    def _related_relations(
        world: WorldState,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entity_ids = {
            entity.get("id")
            for entity in entities
        }

        result: list[dict[str, Any]] = []

        for relation in world.relations.values():
            if not getattr(
                relation,
                "active",
                True,
            ):
                continue

            subject_id = getattr(
                relation,
                "subject_id",
                None,
            )

            target_id = getattr(
                relation,
                "target_id",
                None,
            )

            if (
                subject_id not in entity_ids
                and target_id not in entity_ids
            ):
                continue

            result.append(
                MemorySearchService._relation_to_dict(
                    relation
                )
            )

        result.sort(
            key=lambda relation: str(
                relation.get("id", "")
            )
        )

        return result

    # ============================================================
    # EVENTS
    # ============================================================

    @staticmethod
    def _related_events(
        world: WorldState,
        entities: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        entity_ids = {
            entity.get("id")
            for entity in entities
        }

        result: list[dict[str, Any]] = []

        for event in world.events.values():
            if getattr(
                event,
                "secret",
                False,
            ):
                continue

            metadata = getattr(
                event,
                "metadata",
                None,
            )

            if not isinstance(metadata, dict):
                continue

            related_ids = metadata.get(
                "entity_ids",
                [],
            )

            if not isinstance(
                related_ids,
                (list, tuple, set),
            ):
                continue

            if not entity_ids.intersection(
                related_ids
            ):
                continue

            result.append(
                MemorySearchService._event_to_dict(
                    event
                )
            )

        result.sort(
            key=lambda event: str(
                event.get("id", "")
            )
        )

        return result

    # ============================================================
    # TEXT CONTEXT
    # ============================================================

    @staticmethod
    def _build_text_context(
        result: dict[str, Any],
    ) -> str:
        sections: list[str] = []

        entities = result.get(
            "entities",
            [],
        )

        if entities:
            sections.append(
                "[ENTIDADES]"
            )

            for entity in entities:
                name = entity.get(
                    "name",
                    "Sin nombre",
                )

                entity_type = entity.get(
                    "entity_type",
                    "unknown",
                )

                description = entity.get(
                    "description",
                    "",
                )

                notes = entity.get(
                    "notes",
                    "",
                )

                line = (
                    f"- {name} "
                    f"({entity_type})"
                )

                if description:
                    line += f": {description}"

                if notes:
                    line += (
                        f" Notas: {notes}"
                    )

                sections.append(line)

        relations = result.get(
            "relations",
            [],
        )

        if relations:
            sections.append(
                "[RELACIONES]"
            )

            for relation in relations:
                relation_type = relation.get(
                    "relation_type",
                    "unknown",
                )

                subject_id = relation.get(
                    "subject_id"
                )

                target_id = relation.get(
                    "target_id"
                )

                line = (
                    f"- {relation_type}: "
                    f"{subject_id} -> "
                    f"{target_id}"
                )

                metadata = relation.get(
                    "metadata"
                )

                if isinstance(
                    metadata,
                    dict,
                ):
                    reason = metadata.get(
                        "reason"
                    )

                    if reason:
                        line += (
                            f" Motivo: {reason}"
                        )

                sections.append(line)

        events = result.get(
            "events",
            [],
        )

        if events:
            sections.append(
                "[EVENTOS]"
            )

            for event in events:
                title = event.get(
                    "title",
                    "Sin título",
                )

                description = event.get(
                    "description",
                    "",
                )

                consequences = event.get(
                    "consequences",
                    "",
                )

                line = f"- {title}"

                if description:
                    line += (
                        f": {description}"
                    )

                if consequences:
                    line += (
                        f" Consecuencias: "
                        f"{consequences}"
                    )

                sections.append(line)

        if not sections:
            return "Sin información relevante."

        return "\n".join(sections)

    # ============================================================
    # EMPTY RESULT
    # ============================================================

    @staticmethod
    def _empty_result() -> dict[str, Any]:
        return {
            "query": "",
            "entities": [],
            "items": [],
            "item_instances": [],
            "resources": [],
            "resource_balances": [],
            "relations": [],
            "events": [],
            "context": (
                "Sin información relevante."
            ),
        }