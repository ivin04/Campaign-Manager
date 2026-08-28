from __future__ import annotations

from typing import Any

from models.world_state import WorldState
from services.memory_search_service import MemorySearchService
from services.world_serializer import WorldSerializer
from services.context_ranker import ContextRanker
from services.context_expander import ContextExpander


class ContextBuilder:
    """
    Construye el contexto narrativo para el LLM.

    El proceso se divide en dos fases:

    1. Reunir y enriquecer información estructurada relevante.
    2. Convertir esa información en contexto textual limitado
       por un presupuesto.

    MemorySearchService encuentra candidatos.
    ContextBuilder decide cómo ampliar, priorizar y representar
    esos candidatos dentro del contexto.

    Responsabilidades:

    - Identificar entidades principales.
    - Calcular relevancia.
    - Incluir entidades relacionadas.
    - Incluir relaciones conectadas.
    - Incluir eventos relacionados.
    - Resolver objetos padre necesarios para interpretar resultados.
    - Aplicar un presupuesto máximo de contexto.
    - Construir la representación textual para el LLM.
    - Excluir entidades inactivas.
    - Excluir relaciones inactivas.
    - Excluir eventos secretos.
    - No modificar WorldState.
    - No acceder directamente a SQLite.
    """

    DEFAULT_MAX_DEPTH = 1

    # Se mide en caracteres, no tokens.
    DEFAULT_MAX_CONTEXT_CHARS = 6000

    # ============================================================
    # CONTEXT CANDIDATE SCORING
    # ============================================================

    CATEGORY_BASE_SCORES = {
        "entities": 1.00,
        "relations": 0.80,
        "events": 0.70,
        "items": 0.60,
        "item_instances": 0.50,
        "resources": 0.40,
        "resource_balances": 0.30,
    }

    CATEGORY_PRIORITY = {
        "entities": 0,
        "relations": 1,
        "events": 2,
        "items": 3,
        "item_instances": 4,
        "resources": 5,
        "resource_balances": 6,
    }

    # Compatibilidad con el contrato histórico de ContextBuilder.
    # La implementación real del scoring vive en ContextRanker.

    DIRECT_ENTITY_RELEVANCE = ContextRanker.DIRECT_ENTITY_RELEVANCE
    RELATED_ENTITY_RELEVANCE = ContextRanker.RELATED_ENTITY_RELEVANCE
    DIRECT_MATCH_BONUS = ContextRanker.DIRECT_MATCH_BONUS
    DEFAULT_RELATION_RELEVANCE = (
        ContextRanker.DEFAULT_RELATION_RELEVANCE
    )
    RELATION_RELEVANCE_WEIGHTS = (
        ContextRanker.RELATION_RELEVANCE_WEIGHTS
    )

    # ============================================================
    # INITIALIZATION
    # ============================================================

    def __init__(
        self,
        memory_search_service: MemorySearchService | None = None,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
        ranker: ContextRanker | None = None,
        context_expander: ContextExpander | None = None,
    ) -> None:

        if not isinstance(max_context_chars, int):
            raise TypeError(
                "max_context_chars must be an integer"
            )

        if max_context_chars <= 0:
            raise ValueError(
                "max_context_chars must be > 0"
            )

        self.memory_search_service = (
            memory_search_service
            or MemorySearchService()
        )

        self.max_context_chars = max_context_chars

        if ranker is not None and not isinstance(
            ranker,
            ContextRanker,
        ):
            raise TypeError(
                "ranker must be a ContextRanker"
            )

        self.ranker = ranker or ContextRanker()

        self.context_expander = (
            context_expander
            or ContextExpander(
                ranker=self.ranker,
            )
        )

    # ============================================================
    # PUBLIC API
    # ============================================================

    def build(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, Any]:
        """
        Construye el contexto completo para el LLM.

        Primero reúne los datos estructurados relevantes y después
        genera una representación textual respetando el presupuesto
        configurado.
        """

        self._validate_world(world)

        normalized_query = self._validate_query(query)

        if not normalized_query:
            return self._empty_result()

        result = self._build_context_data(
            world,
            normalized_query,
        )

        result["context"] = self._build_text_context(
            result
        )

        self._strip_internal_context_fields(
            result
        )

        return result

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate_world(
        world: WorldState,
    ) -> None:

        if not isinstance(world, WorldState):
            raise TypeError(
                "world must be a WorldState"
            )

    @staticmethod
    def _validate_query(
        query: str,
    ) -> str:

        if not isinstance(query, str):
            raise TypeError(
                "query must be a string"
            )

        return query.strip()

    # ============================================================
    # CONTEXT DATA
    # ============================================================

    def _build_context_data(
        self,
        world: WorldState,
        normalized_query: str,
    ) -> dict[str, Any]:
        """
        Construye los datos estructurados relevantes.

        Esta fase NO aplica el presupuesto textual.

        La búsqueda inicial se delega en
        MemorySearchService y la expansión de contexto
        se delega en ContextExpander.
        """

        search_result = (
            self.memory_search_service.search(
                world,
                normalized_query,
            )
        )

        result = self.context_expander.expand(
            world,
            search_result,
        )

        result["query"] = normalized_query

        return result

    # ============================================================
    # TEXT CONTEXT
    # ============================================================

    def _build_text_context(
        self,
        result: dict[str, Any],
    ) -> str:
        """
        Construye el contexto textual final.

        1. Crear candidatos.
        2. Calcular relevancia.
        3. Ordenar por score.
        4. Seleccionar dentro del presupuesto.
        5. Renderizar.
        """

        query = str(
            result.get(
                "query",
                "",
            )
        ).strip().casefold()

        candidates = (
            self._build_context_candidates(
                result,
                query,
            )
        )

        if not candidates:
            return "Sin información relevante."

        candidates.sort(
            key=lambda candidate: (
                -candidate["score"],
                candidate["category_order"],
                candidate["index"],
            )
        )

        selected: list[dict[str, Any]] = []

        current_length = 0
        selected_categories: set[str] = set()

        for candidate in candidates:

            category = candidate["category"]
            text = candidate["text"]

            header = self._category_header(
                category
            )

            additional_length = len(text)

            if current_length > 0:
                additional_length += 1

            if category not in selected_categories:

                additional_length += len(
                    header
                )

                if current_length > 0:
                    additional_length += 1

            projected_length = (
                current_length
                + additional_length
            )

            if projected_length > self.max_context_chars:
                continue

            selected.append(candidate)

            current_length = projected_length
            selected_categories.add(
                category
            )

        if not selected:
            return "Sin información relevante."

        selected.sort(
            key=lambda candidate: (
                candidate["category_order"],
                candidate["index"],
                -candidate["score"],
            )
        )

        return self._render_selected_candidates(
            selected
        )

    # ============================================================
    # CONTEXT CANDIDATES
    # ============================================================

    def _build_context_candidates(
        self,
        result: dict[str, Any],
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Convierte la información disponible en candidatos
        independientes de contexto.

        Cada candidato contiene:

            category
            text
            score
            category_order
            index

        Importante:

        Este método es de instancia porque utiliza
        self.ranker.
        """

        candidates: list[dict[str, Any]] = []

        category_definitions = [
            (
                "entities",
                self.CATEGORY_BASE_SCORES["entities"],
                self.CATEGORY_PRIORITY["entities"],
                self._entity_lines,
            ),
            (
                "relations",
                self.CATEGORY_BASE_SCORES["relations"],
                self.CATEGORY_PRIORITY["relations"],
                self._relation_lines,
            ),
            (
                "events",
                self.CATEGORY_BASE_SCORES["events"],
                self.CATEGORY_PRIORITY["events"],
                self._event_lines,
            ),
            (
                "items",
                self.CATEGORY_BASE_SCORES["items"],
                self.CATEGORY_PRIORITY["items"],
                self._item_lines,
            ),
            (
                "item_instances",
                self.CATEGORY_BASE_SCORES["item_instances"],
                self.CATEGORY_PRIORITY["item_instances"],
                self._item_instance_lines,
            ),
            (
                "resources",
                self.CATEGORY_BASE_SCORES["resources"],
                self.CATEGORY_PRIORITY["resources"],
                self._resource_lines,
            ),
            (
                "resource_balances",
                self.CATEGORY_BASE_SCORES["resource_balances"],
                self.CATEGORY_PRIORITY["resource_balances"],
                self._resource_balance_lines,
            ),
        ]

        for (
            category,
            base_score,
            category_order,
            line_builder,
        ) in category_definitions:

            values = result.get(
                category,
                [],
            )

            if not isinstance(
                values,
                list,
            ):
                continue

            for index, value in enumerate(values):

                if not isinstance(
                    value,
                    dict,
                ):
                    continue

                lines = line_builder(
                    [value]
                )

                if not lines:
                    continue

                text = lines[0]

                score = float(
                    base_score
                )

                # ------------------------------------------------
                # RELEVANCIA PROPIA DE ENTIDAD
                # ------------------------------------------------

                if category == "entities":

                    relevance = value.get(
                        "_relevance",
                        self.DIRECT_ENTITY_RELEVANCE,
                    )

                    try:
                        relevance = float(
                            relevance
                        )
                    except (
                        TypeError,
                        ValueError,
                    ):
                        relevance = (
                            self.DIRECT_ENTITY_RELEVANCE
                        )

                    score = relevance

                # ------------------------------------------------
                # COINCIDENCIA DIRECTA
                # ------------------------------------------------

                score += (
                    self.ranker.direct_match_bonus(
                        value,
                        query,
                    )
                )

                candidates.append(
                    {
                        "category": category,
                        "text": text,
                        "score": score,
                        "category_order": category_order,
                        "index": index,
                    }
                )

        return candidates

    # ============================================================
    # CANDIDATE LINE BUILDERS
    # ============================================================

    @staticmethod
    def _entity_lines(
        entities: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

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
                line += (
                    f": {description}"
                )

            if notes:
                line += (
                    f" Notas: {notes}"
                )

            lines.append(line)

        return lines

    @staticmethod
    def _relation_lines(
        relations: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

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

            lines.append(line)

        return lines

    @staticmethod
    def _event_lines(
        events: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

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

            lines.append(line)

        return lines

    @staticmethod
    def _item_lines(
        items: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

        for item in items:

            name = item.get(
                "name",
                "Sin nombre",
            )

            description = item.get(
                "description",
                "",
            )

            significance = item.get(
                "significance",
                "",
            )

            notes = item.get(
                "notes",
                "",
            )

            line = f"- {name}"

            if description:
                line += (
                    f": {description}"
                )

            if significance:
                line += (
                    f" Importancia: "
                    f"{significance}"
                )

            if notes:
                line += (
                    f" Notas: {notes}"
                )

            lines.append(line)

        return lines

    @staticmethod
    def _item_instance_lines(
        instances: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

        for instance in instances:

            instance_id = instance.get(
                "id",
                "unknown",
            )

            item_id = instance.get(
                "item_id"
            )

            owner_id = instance.get(
                "owner_id"
            )

            location_id = instance.get(
                "location_id"
            )

            line = (
                f"- Instancia "
                f"{instance_id}"
            )

            if item_id is not None:
                line += (
                    f" item={item_id}"
                )

            if owner_id is not None:
                line += (
                    f" propietario="
                    f"{owner_id}"
                )

            if location_id is not None:
                line += (
                    f" ubicación="
                    f"{location_id}"
                )

            lines.append(line)

        return lines

    @staticmethod
    def _resource_lines(
        resources: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

        for resource in resources:

            name = resource.get(
                "name",
                "Sin nombre",
            )

            resource_type = resource.get(
                "resource_type",
                "",
            )

            unit = resource.get(
                "unit",
                "",
            )

            notes = resource.get(
                "notes",
                "",
            )

            line = f"- {name}"

            if resource_type:
                line += (
                    f" ({resource_type})"
                )

            if unit:
                line += (
                    f" Unidad: {unit}"
                )

            if notes:
                line += (
                    f" Notas: {notes}"
                )

            lines.append(line)

        return lines

    @staticmethod
    def _resource_balance_lines(
        balances: list[dict[str, Any]],
    ) -> list[str]:

        lines: list[str] = []

        for balance in balances:

            balance_id = balance.get(
                "id",
                "unknown",
            )

            resource_id = balance.get(
                "resource_id"
            )

            owner_id = balance.get(
                "owner_id"
            )

            amount = balance.get(
                "amount"
            )

            line = (
                f"- Balance "
                f"{balance_id}"
            )

            if resource_id is not None:
                line += (
                    f" recurso="
                    f"{resource_id}"
                )

            if owner_id is not None:
                line += (
                    f" propietario="
                    f"{owner_id}"
                )

            if amount is not None:
                line += (
                    f" cantidad="
                    f"{amount}"
                )

            lines.append(line)

        return lines

    # ============================================================
    # CATEGORY HELPERS
    # ============================================================

    @staticmethod
    def _category_header(
        category: str,
    ) -> str:
        """
        Devuelve el encabezado público de una categoría.
        """

        headers = {
            "entities": "[ENTIDADES]",
            "relations": "[RELACIONES]",
            "events": "[EVENTOS]",
            "items": "[ITEMS]",
            "item_instances": "[ITEM_INSTANCES]",
            "resources": "[RESOURCES]",
            "resource_balances": "[RESOURCE_BALANCES]",
        }

        return headers.get(
            category,
            f"[{category.upper()}]",
        )

    # ============================================================
    # CONTEXT RENDERING
    # ============================================================

    def _render_selected_candidates(
        self,
        candidates: list[dict[str, Any]],
    ) -> str:
        """
        Renderiza los candidatos seleccionados agrupándolos
        por categoría.

        Este método es de instancia porque utiliza
        self._category_header().
        """

        if not candidates:
            return "Sin información relevante."

        sections: list[str] = []

        current_category: str | None = None

        for candidate in candidates:

            category = candidate["category"]

            if category != current_category:

                sections.append(
                    self._category_header(
                        category
                    )
                )

                current_category = category

            sections.append(
                candidate["text"]
            )

        return "\n".join(
            sections
        )

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

    # ============================================================
    # INTERNAL FIELD CLEANUP
    # ============================================================

    @staticmethod
    def _strip_internal_context_fields(
        result: dict[str, Any],
    ) -> None:
        """
        Elimina metadatos internos de relevancia antes de devolver
        el resultado público.
        """

        for entity in result.get(
            "entities",
            [],
        ):

            if not isinstance(
                entity,
                dict,
            ):
                continue

            entity.pop(
                "_relevance",
                None,
            )

            entity.pop(
                "_depth",
                None,
            )

    # ============================================================
    # RANKER COMPATIBILITY HELPERS
    # ============================================================

    def _get_relation_relevance(
        self,
        relation_type: str,
    ) -> float:

        return self.ranker.get_relation_relevance(
            relation_type
        )

    def _entity_context_score(
        self,
        entity: dict[str, Any],
        query: str,
    ) -> float:

        return self.ranker.entity_context_score(
            entity,
            query,
        )

    def _direct_match_bonus(
        self,
        data: dict[str, Any],
        query: str,
    ) -> float:

        return self.ranker.direct_match_bonus(
            data,
            query,
        )

    def _score_context_candidate(
        self,
        text: str,
        query: str,
        base_score: float,
    ) -> float:

        return self.ranker.score_context_candidate(
            text,
            query,
            base_score,
        )
