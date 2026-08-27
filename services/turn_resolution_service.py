from __future__ import annotations

from models.operation_result import OperationResult
from models.turn_resolution_result import TurnResolutionResult
from models.world_state import WorldState
from operations.world_operations import WorldOperation
from services.dm_service import DMService
from services.llm_world_extractor import LLMWorldExtractor
from services.world_service import WorldService


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
        WorldService.apply_operations()
           |
           v
        resultado atómico

    Responsabilidades:

    - validar WorldState
    - validar entrada del jugador
    - generar narrativa mediante DMService
    - extraer operaciones mediante LLMWorldExtractor
    - aplicar operaciones de forma atómica mediante WorldService
    - devolver TurnResolutionResult

    NO debe:

    - acceder directamente a WorldApplier
    - acceder a SQLite
    - persistir directamente
    - conocer Ollama
    - conocer el modelo LLM
    - construir prompts
    - interpretar JSON
    - implementar reglas de dominio
    - reconstruir el contexto después de resolver el turno
    """

    def __init__(
        self,
        dm_service: DMService,
        extractor: LLMWorldExtractor,
        world_service: WorldService,
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
                "extractor must be a LLMWorldExtractor"
            )

        if not isinstance(
            world_service,
            WorldService,
        ):
            raise TypeError(
                "world_service must be a WorldService"
            )

        self.dm_service = dm_service
        self.extractor = extractor
        self.world_service = world_service

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
            3. aplicación atómica

        Si una operación falla:

            - ninguna operación queda aplicada
            - el WorldState original se conserva

        La persistencia en SQLite NO se realiza aquí.
        """

        self._validate_world(world)

        normalized_input = self._validate_player_input(
            player_input
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
        # 3. APLICAR OPERACIONES DE FORMA ATÓMICA
        # ========================================================

        try:
            application = self.world_service.apply_operations(
                operations
            )

        except Exception as exc:
            raise TurnResolutionServiceError(
                "WorldService failed to apply operations"
            ) from exc

        if not isinstance(
            application,
            dict,
        ):
            raise TurnResolutionServiceError(
                "WorldService returned an invalid application result"
            )

        success = application.get(
            "success",
            False,
        )

        results = application.get(
            "results",
            [],
        )

        if not isinstance(
            success,
            bool,
        ):
            raise TurnResolutionServiceError(
                "WorldService returned an invalid success value"
            )

        if not isinstance(
            results,
            list,
        ):
            raise TurnResolutionServiceError(
                "WorldService returned invalid operation results"
            )

        for result in results:

            if not isinstance(
                result,
                OperationResult,
            ):
                raise TurnResolutionServiceError(
                    "WorldService returned an invalid OperationResult"
                )

        # ========================================================
        # 4. RESULTADO
        # ========================================================

        return TurnResolutionResult(
            player_input=normalized_input,
            narrative=narrative,
            operations=tuple(operations),
            operation_results=tuple(results),
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