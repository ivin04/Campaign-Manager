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
    - Calcular relevancia.
    - Incluir entidades relacionadas.
    - Incluir relaciones conectadas.
    - Incluir eventos relacionados.
    - Aplicar un presupuesto máximo de contexto.
    - Excluir entidades inactivas.
    - Excluir relaciones inactivas.
    - Excluir eventos secretos.
    - No modificar WorldState.
    - No acceder directamente a SQLite.
    """

    DEFAULT_MAX_DEPTH = 1

    # Presupuesto inicial conservador.
    #
    # Se mide en caracteres, no tokens.
    # Más adelante podremos sustituirlo por un tokenizer real
    # cuando sepamos qué modelo utilizará el DM.
    DEFAULT_MAX_CONTEXT_CHARS = 6000

    DIRECT_ENTITY_RELEVANCE = 1.0
    RELATED_ENTITY_RELEVANCE = 0.7

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

    DIRECT_MATCH_BONUS = 0.25

    # ============================================================
    # RELATION RELEVANCE
    # ============================================================

    DEFAULT_RELATION_RELEVANCE = 0.70

    RELATION_RELEVANCE_WEIGHTS = {
        # Relaciones sociales / narrativas fuertes
        "friend": 1.00,
        "friendship": 1.00,
        "ally": 1.00,
        "alliance": 1.00,
        "family": 1.00,
        "parent": 1.00,
        "child": 1.00,

        # Relaciones hostiles
        "enemy": 0.95,
        "rival": 0.90,
        "hostile": 0.90,

        # Relaciones de pertenencia / proximidad
        "owner": 0.90,
        "owns": 0.90,
        "member": 0.85,
        "member_of": 0.85,

        # Relaciones espaciales
        "lives_in": 0.75,
        "located_in": 0.75,
        "resident_of": 0.75,

        # Relaciones débiles
        "knows": 0.65,
        "met": 0.60,
        "works_with": 0.80,
    }

    def __init__(
        self,
        memory_search_service: MemorySearchService | None = None,
        max_context_chars: int = DEFAULT_MAX_CONTEXT_CHARS,
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

    def build(
        self,
        world: WorldState,
        query: str,
    ) -> dict[str, Any]:
        """
        Construye contexto relacionado a partir de una consulta.

        El resultado mantiene las categorías públicas existentes,
        pero las entidades se ordenan por relevancia y el texto
        final respeta el presupuesto máximo configurado.
        """

        self._validate_world(world)

        normalized_query = self._validate_query(query)

        if not normalized_query:
            return self._empty_result()

        search_result = self.memory_search_service.search(
            world,
            normalized_query,
        )

        search_result = self._resolve_parent_objects(
            world,
            search_result,
        )

        entities = self._expand_entities(
            world,
            search_result["entities"],
            max_depth=self.DEFAULT_MAX_DEPTH,
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
            "items": search_result["items"],
            "item_instances": search_result["item_instances"],
            "resources": search_result["resources"],
            "resource_balances": search_result[
                "resource_balances"
            ],
            "relations": relations,
            "events": events,
        }

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
    # ENTITY EXPANSION + RELEVANCE
    # ============================================================

    def _expand_entities(
        self,
        world: WorldState,
        matched_entities: list[dict[str, Any]],
        max_depth: int = 1,
    ) -> list[dict[str, Any]]:
        """
        Amplía las entidades encontradas siguiendo relaciones activas.

        La relevancia se propaga por el grafo.

        Una entidad directa empieza con:

            1.0

        Una entidad relacionada recibe:

            relevancia_origen
            * peso_relacion
            * factor_profundidad

        De esta forma una relación fuerte conserva más relevancia
        que una relación débil.

        La función no modifica WorldState.
        """

        if max_depth < 0:
            raise ValueError(
                "max_depth must be >= 0"
            )

        entity_depths: dict[int, int] = {}
        entity_relevance: dict[int, float] = {}

        # --------------------------------------------------------
        # ENTIDADES DIRECTAMENTE ENCONTRADAS
        # --------------------------------------------------------

        for entity in matched_entities:
            entity_id = entity.get("id")

            if not isinstance(entity_id, int):
                continue

            entity_depths[entity_id] = 0

            entity_relevance[entity_id] = (
                self.DIRECT_ENTITY_RELEVANCE
            )

        # --------------------------------------------------------
        # EXPANSIÓN DEL GRAFO
        # --------------------------------------------------------

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

                relation_type = getattr(
                    relation,
                    "relation_type",
                    "",
                )

                relation_weight = (
                    self._get_relation_relevance(
                        relation_type
                    )
                )

                # ------------------------------------------------
                # FACTOR DE PROFUNDIDAD
                # ------------------------------------------------

                depth_factor = (
                    self.RELATED_ENTITY_RELEVANCE
                    ** (depth + 1)
                )

                propagation_factor = (
                    relation_weight
                    * depth_factor
                )

                # ------------------------------------------------
                # SUBJECT -> TARGET
                # ------------------------------------------------

                if subject_id in current_ids:

                    if (
                        target_id in world.entities
                        and getattr(
                            world.entities[target_id],
                            "active",
                            True,
                        )
                    ):
                        candidate_relevance = (
                            entity_relevance[subject_id]
                            * propagation_factor
                        )

                        self._register_related_entity(
                            entity_depths,
                            entity_relevance,
                            target_id,
                            depth + 1,
                            candidate_relevance,
                        )

                # ------------------------------------------------
                # TARGET -> SUBJECT
                # ------------------------------------------------

                if target_id in current_ids:

                    if (
                        subject_id in world.entities
                        and getattr(
                            world.entities[subject_id],
                            "active",
                            True,
                        )
                    ):
                        candidate_relevance = (
                            entity_relevance[target_id]
                            * propagation_factor
                        )

                        self._register_related_entity(
                            entity_depths,
                            entity_relevance,
                            subject_id,
                            depth + 1,
                            candidate_relevance,
                        )

        # --------------------------------------------------------
        # CONSTRUIR RESULTADO
        # --------------------------------------------------------

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

            entity_data = (
                self.memory_search_service._entity_to_dict(
                    entity
                )
            )

            entity_data["_relevance"] = (
                entity_relevance.get(
                    entity_id,
                    0.0,
                )
            )

            entity_data["_depth"] = (
                entity_depths.get(
                    entity_id,
                    max_depth + 1,
                )
            )

            result.append(
                entity_data
            )

        # --------------------------------------------------------
        # ORDENAR
        # --------------------------------------------------------

        result.sort(
            key=lambda entity: (
                -entity.get(
                    "_relevance",
                    0.0,
                ),
                entity.get(
                    "_depth",
                    max_depth + 1,
                ),
                entity.get(
                    "id",
                    0,
                ),
            )
        )

        # --------------------------------------------------------
        # LIMPIAR CAMPOS INTERNOS
        # --------------------------------------------------------

        return result

    @classmethod
    def _get_relation_relevance(
        cls,
        relation_type: Any,
    ) -> float:
        """
        Devuelve el peso de propagación de una relación.

        La comparación es case-insensitive y tolera valores
        no string.
        """

        if relation_type is None:
            return cls.DEFAULT_RELATION_RELEVANCE

        normalized = str(
            relation_type
        ).strip().casefold()

        if not normalized:
            return cls.DEFAULT_RELATION_RELEVANCE

        return cls.RELATION_RELEVANCE_WEIGHTS.get(
            normalized,
            cls.DEFAULT_RELATION_RELEVANCE,
        )

    @staticmethod
    def _register_related_entity(
        entity_depths: dict[int, int],
        entity_relevance: dict[int, float],
        entity_id: int,
        depth: int,
        relevance: float,
    ) -> None:
        """
        Registra una entidad relacionada.

        Si ya existe por otro camino del grafo, conserva
        la mayor relevancia encontrada.

        Esto evita que un camino débil sobrescriba uno fuerte.
        """

        existing_depth = entity_depths.get(
            entity_id
        )

        existing_relevance = entity_relevance.get(
            entity_id,
            0.0,
        )

        if existing_depth is None:
            entity_depths[entity_id] = depth
            entity_relevance[entity_id] = relevance
            return

        if relevance > existing_relevance:
            entity_relevance[entity_id] = relevance

        if depth < existing_depth:
            entity_depths[entity_id] = depth

    def _entity_context_score(
        self,
        entity: dict[str, Any],
        query: str,
    ) -> float:
        """
        Conserva la relevancia relacional calculada previamente
        y añade una pequeña bonificación por coincidencia directa.
        """

        relevance = entity.get(
            "_relevance",
            self.DIRECT_ENTITY_RELEVANCE,
        )

        try:
            relevance = float(relevance)
        except (TypeError, ValueError):
            relevance = self.DIRECT_ENTITY_RELEVANCE

        return (
            relevance
            + self._direct_match_bonus(
                entity,
                query,
            )
        )

    def _direct_match_bonus(
        self,
        data: dict[str, Any],
        query: str,
    ) -> float:
        """
        Añade una pequeña bonificación cuando la consulta aparece
        directamente en los datos del candidato.
        """

        if not query:
            return 0.0

        searchable_fields = (
            "name",
            "description",
            "title",
            "notes",
            "significance",
            "relation_type",
            "event_type",
            "resource_type",
            "unit",
        )

        for field in searchable_fields:

            value = data.get(field)

            if value is None:
                continue

            if query in str(value).casefold():
                return self.DIRECT_MATCH_BONUS

        return 0.0

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
                relation.get(
                    "id",
                    "",
                )
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

            if not isinstance(
                metadata,
                dict,
            ):
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
                event.get(
                    "id",
                    "",
                )
            )
        )

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

        El proceso es:

            1. Crear candidatos.
            2. Calcular relevancia.
            3. Ordenar por score.
            4. Seleccionar dentro del presupuesto.
            5. Agrupar por categoría.
            6. Renderizar.

        El presupuesto incluye también los headers.
        """

        query = str(
            result.get(
                "query",
                "",
            )
        ).strip().casefold()

        candidates = self._build_context_candidates(
            result,
            query,
        )

        if not candidates:
            return "Sin información relevante."

        # --------------------------------------------------------
        # ORDEN DE SELECCIÓN
        # --------------------------------------------------------

        candidates.sort(
            key=lambda candidate: (
                -candidate["score"],
                candidate["category_order"],
                candidate["index"],
            )
        )

        # --------------------------------------------------------
        # SELECCIÓN DENTRO DEL PRESUPUESTO
        # --------------------------------------------------------

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

            # Separador antes de la línea.
            if current_length > 0:
                additional_length += 1

            # Si todavía no hemos incluido esta categoría,
            # necesitamos reservar espacio para su header.
            if category not in selected_categories:
                additional_length += len(header)

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
            selected_categories.add(category)

        if not selected:
            return "Sin información relevante."

        # --------------------------------------------------------
        # AGRUPAR PARA RENDERIZAR
        # --------------------------------------------------------

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

    @classmethod
    def _build_context_candidates(
        cls,
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

        La relevancia específica de las entidades se conserva
        mediante _relevance mientras el contexto se construye.
        """

        candidates: list[dict[str, Any]] = []

        category_definitions = [
            (
                "entities",
                1.00,
                0,
                cls._entity_lines,
            ),
            (
                "relations",
                0.80,
                1,
                cls._relation_lines,
            ),
            (
                "events",
                0.70,
                2,
                cls._event_lines,
            ),
            (
                "items",
                0.60,
                3,
                cls._item_lines,
            ),
            (
                "item_instances",
                0.50,
                4,
                cls._item_instance_lines,
            ),
            (
                "resources",
                0.40,
                5,
                cls._resource_lines,
            ),
            (
                "resource_balances",
                0.30,
                6,
                cls._resource_balance_lines,
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

            if not isinstance(values, list):
                continue

            for index, value in enumerate(values):

                if not isinstance(value, dict):
                    continue

                lines = line_builder([value])

                if not lines:
                    continue

                text = lines[0]

                score = base_score

                # ------------------------------------------------
                # RELEVANCIA PROPIA DE LA ENTIDAD
                # ------------------------------------------------

                if category == "entities":

                    relevance = value.get(
                        "_relevance",
                        cls.DIRECT_ENTITY_RELEVANCE,
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
                            cls.DIRECT_ENTITY_RELEVANCE
                        )

                    score = relevance

                # ------------------------------------------------
                # COINCIDENCIA DIRECTA
                # ------------------------------------------------

                score += cls._direct_match_bonus(
                    value,
                    query,
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

    @staticmethod
    def _direct_match_bonus(
        data: dict[str, Any],
        query: str,
    ) -> float:
        """
        Añade relevancia cuando la consulta coincide directamente
        con algún campo narrativo del candidato.
        """

        if not query:
            return 0.0

        query_normalized = query.casefold()

        searchable_fields = (
            "name",
            "description",
            "title",
            "notes",
            "significance",
            "relation_type",
            "event_type",
            "resource_type",
            "unit",
        )

        for field in searchable_fields:

            value = data.get(field)

            if value is None:
                continue

            normalized_value = str(
                value
            ).casefold()

            if query_normalized in normalized_value:
                return 0.25

        return 0.0

    @staticmethod
    def _score_context_candidate(
        text: str,
        query: str,
        base_score: float,
    ) -> float:
        """
        Calcula la relevancia de una pieza individual.

        La puntuación base representa la importancia de la
        categoría.

        Una coincidencia directa con la consulta aumenta
        la puntuación.

        Se utiliza texto completo de la línea únicamente
        para el ranking; no se modifica la salida.
        """

        score = base_score

        if not query:
            return score

        normalized_text = text.casefold()

        if query in normalized_text:
            score += 0.50

        # Coincidencia por palabras.
        query_words = {
            word
            for word in query.split()
            if word
        }

        if query_words:
            matched_words = sum(
                1
                for word in query_words
                if word in normalized_text
            )

            score += (
                0.10
                * matched_words
            )

        return score

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
    # CONTEXT RENDERING
    # ============================================================

    @classmethod
    def _render_selected_candidates(
        cls,
        candidates: list[dict[str, Any]],
    ) -> str:
        """
        Renderiza los candidatos seleccionados agrupándolos
        por categoría.

        Los candidatos ya han sido seleccionados por relevancia.
        Aquí únicamente se les da una estructura legible.
        """

        if not candidates:
            return "Sin información relevante."

        sections: list[str] = []

        current_category: str | None = None

        for candidate in candidates:

            category = candidate["category"]

            if category != current_category:

                sections.append(
                    cls._category_header(
                        category
                    )
                )

                current_category = category

            sections.append(
                candidate["text"]
            )

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

    def _resolve_parent_objects(
        self,
        world: WorldState,
        search_result: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Completa los resultados con los objetos padre de:

        ItemInstance -> Item
        ResourceBalance -> Resource

        Esto permite que el contexto sea interpretable incluso
        cuando la búsqueda encuentra solamente la instancia o balance.
        """

        result = {
            key: list(value) if isinstance(value, list) else value
            for key, value in search_result.items()
        }

        # =========================================================
        # ITEM INSTANCES -> ITEMS
        # =========================================================

        existing_item_ids = {
            item.get("id")
            for item in result.get("items", [])
            if isinstance(item, dict)
        }

        for instance in result.get(
            "item_instances",
            [],
        ):
            if not isinstance(instance, dict):
                continue

            item_id = instance.get("item_id")

            if item_id is None:
                continue

            if item_id in existing_item_ids:
                continue

            item = world.items.get(item_id)

            if item is None:
                continue

            result["items"].append(
                self.memory_search_service._item_to_dict(
                    item
                )
            )

            existing_item_ids.add(item_id)

        # =========================================================
        # RESOURCE BALANCES -> RESOURCES
        # =========================================================

        existing_resource_ids = {
            resource.get("id")
            for resource in result.get(
                "resources",
                [],
            )
            if isinstance(resource, dict)
        }

        for balance in result.get(
            "resource_balances",
            [],
        ):
            if not isinstance(balance, dict):
                continue

            resource_id = balance.get(
                "resource_id"
            )

            if resource_id is None:
                continue

            if resource_id in existing_resource_ids:
                continue

            resource = world.resources.get(
                resource_id
            )

            if resource is None:
                continue

            result["resources"].append(
                self.memory_search_service._resource_to_dict(
                    resource
                )
            )

            existing_resource_ids.add(
                resource_id
            )

        return result

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
            if not isinstance(entity, dict):
                continue

            entity.pop(
                "_relevance",
                None,
            )

            entity.pop(
                "_depth",
                None,
            )

    @staticmethod
    def _category_header(
        category: str,
    ) -> str:
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