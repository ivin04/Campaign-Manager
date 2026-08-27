from __future__ import annotations

from models.operation_result import OperationResult
from models.turn_resolution_result import TurnResolutionResult
from models.world_state import WorldState
from operations.world_operations import WorldOperation
from services.dm_service import DMService
from services.llm_world_extractor import LLMWorldExtractor
from services.world_applier import WorldApplier


class TurnResolutionServiceError(RuntimeError):
    """
    Error base del servicio de resolución de turnos.
    """


class TurnResolutionService:
    """
    Orquesta la resolución completa de un turno.

    Flujo:

        jugador
           |
           v
        DMService
           |
           v
        narrativa
           |
           v
        LLMWorldExtractor
           |
           v
        WorldOperation[]
           |
           v
        WorldApplier
           |
           v
        WorldState actualizado


    Responsabilidades:

    - validar WorldState
    - validar entrada del jugador
    - generar narrativa mediante DMService
    - extraer operaciones mediante LLMWorldExtractor
    - aplicar operaciones mediante WorldApplier
    - devolver TurnResolutionResult

    NO debe:

    - acceder a SQLite
    - persistir directamente
    - conocer Ollama
    - conocer el modelo LLM
    - construir prompts
    - interpretar JSON
    - implementar reglas de dominio

    Cada dependencia mantiene una única responsabilidad.
    """

    def __init__(
        self,
        dm_service: DMService,
        extractor: LLMWorldExtractor,
        world_applier: WorldApplier,
    ) -> None:

        if not isinstance(
            dm_service,
            DMService,
        ):
            raise TypeError(
                "dm_service must be a DMService"
            )

        if not isinstance(
            extractor,
            LLMWorldExtractor,
        ):
            raise TypeError(
                "extractor must be an LLMWorldExtractor"
            )

        if not isinstance(
            world_applier,
            WorldApplier,
        ):
            raise TypeError(
                "world_applier must be a WorldApplier"
            )

        self.dm_service = dm_service
        self.extractor = extractor
        self.world_applier = world_applier

    # ============================================================
    # PUBLIC API
    # ============================================================

    def resolve_turn(
        self,
        world: WorldState,
        player_input: str,
    ) -> TurnResolutionResult:
        """
        Resuelve un turno completo.

        Orden estricto:

            1. narrativa
            2. extracción
            3. aplicación

        """

        self._validate_world(world)

        normalized_input = (
            self._validate_player_input(
                player_input
            )
        )

        if not normalized_input:
            raise TurnResolutionServiceError(
                "player_input must not be empty"
            )

        # ========================================================
        # 1. GENERAR NARRATIVA
        # ========================================================

        try:
            narrative = self.dm_service.generate(
                world,
                normalized_input,
            )
        except Exception as exc:
            raise TurnResolutionServiceError(
                "DMService failed to generate the turn"
            ) from exc

        if not isinstance(
            narrative,
            str,
        ):
            raise TurnResolutionServiceError(
                "DMService returned a non-string narrative"
            )

        narrative = narrative.strip()

        if not narrative:
            raise TurnResolutionServiceError(
                "DMService returned an empty narrative"
            )

        # ========================================================
        # 2. EXTRAER OPERACIONES
        # ========================================================

        try:
            operations = self.extractor.extract(
                narrative,
                world,
            )
        except Exception as exc:
            raise TurnResolutionServiceError(
                "LLMWorldExtractor failed to extract operations"
            ) from exc

        if not isinstance(
            operations,
            list,
        ):
            raise TurnResolutionServiceError(
                "LLMWorldExtractor returned an invalid operations list"
            )

        for operation in operations:
            if not isinstance(
                operation,
                WorldOperation,
            ):
                raise TurnResolutionServiceError(
                    "LLMWorldExtractor returned "
                    "an invalid WorldOperation"
                )

        # ========================================================
        # 3. APLICAR OPERACIONES
        # ========================================================

        operation_results: list[
            OperationResult
        ] = []

        for operation in operations:

            try:
                result = self.world_applier.apply(
                    world,
                    operation,
                )
            except Exception as exc:
                raise TurnResolutionServiceError(
                    "WorldApplier failed to apply an operation"
                ) from exc

            if not isinstance(
                result,
                OperationResult,
            ):
                raise TurnResolutionServiceError(
                    "WorldApplier returned an invalid OperationResult"
                )

            operation_results.append(
                result
            )

        # ========================================================
        # 4. CONTEXTO
        # ========================================================

        context = ""

        context_builder = getattr(
            self.dm_service,
            "context_builder",
            None,
        )

        if context_builder is not None:

            try:
                context_result = (
                    context_builder.build(
                        world,
                        normalized_input,
                    )
                )
            except Exception:
                context_result = None

            if isinstance(
                context_result,
                dict,
            ):
                candidate_context = (
                    context_result.get(
                        "context",
                        "",
                    )
                )

                if isinstance(
                    candidate_context,
                    str,
                ):
                    context = candidate_context

        # ========================================================
        # 5. RESULTADO
        # ========================================================

        return TurnResolutionResult(
            player_input=normalized_input,
            narrative=narrative,
            operations=tuple(
                operations
            ),
            operation_results=tuple(
                operation_results
            ),
            context=context,
        )
    

    # ============================================================
    # VALIDATION
    # ============================================================

    @staticmethod
    def _validate_world(
        world: WorldState,
    ) -> None:

        if not isinstance(
            world,
            WorldState,
        ):
            raise TypeError(
                "world must be a WorldState"
            )

    @staticmethod
    def _validate_player_input(
        player_input: str,
    ) -> str:

        if not isinstance(
            player_input,
            str,
        ):
            raise TypeError(
                "player_input must be a string"
            )

        return player_input.strip()