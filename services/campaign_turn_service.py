from __future__ import annotations

from models.turn_resolution_result import TurnResolutionResult
from models.world_state import WorldState

from services.turn_resolution_service import (
    TurnResolutionService,
    TurnResolutionServiceError,
)
from services.world_service import WorldService


class CampaignTurnServiceError(RuntimeError):
    """
    Error base del servicio de turno de campaña.
    """


class CampaignTurnService:
    """
    Fachada de alto nivel para ejecutar un turno completo de campaña.

    Responsabilidad:

        campaña
           |
           v
        WorldService
           |
           v
        WorldState
           |
           v
        TurnResolutionService
           |
           +--> DMService
           |
           +--> LLMWorldExtractor
           |
           +--> WorldApplier
           |
           v
        WorldState actualizado y persistido

    Este servicio es la frontera entre la aplicación y el motor
    de resolución de turnos.

    TurnResolutionService:
        - resuelve el turno
        - delega la aplicación y persistencia atómica
        de las operaciones en WorldService

    WorldService:
        - mantiene WorldState
        - aplica operaciones
        - garantiza la consistencia entre el estado
        en memoria y la persistencia
        - no conoce la narrativa del turno

    CampaignTurnService:
        - obtiene el WorldState actual
        - delega la resolución del turno
        - traduce errores de la capa de resolución
    """

    def __init__(
        self,
        *,
        turn_resolution_service: TurnResolutionService,
        world_service: WorldService,
    ) -> None:

        if not isinstance(
            turn_resolution_service,
            TurnResolutionService,
        ):
            raise TypeError(
                "turn_resolution_service must be a "
                "TurnResolutionService"
            )

        if not isinstance(
            world_service,
            WorldService,
        ):
            raise TypeError(
                "world_service must be a WorldService"
            )

        self.turn_resolution_service = (
            turn_resolution_service
        )

        self.world_service = world_service

    # ============================================================
    # PUBLIC API
    # ============================================================

    def play_turn(
        self,
        player_input: str,
    ) -> TurnResolutionResult:
        """
        Ejecuta un turno sobre la campaña actualmente cargada.

        Flujo:

            1. Obtener WorldState actual.
            2. Resolver el turno.
            3. Devolver el resultado.

        La resolución narrativa y de operaciones pertenece
        exclusivamente a TurnResolutionService.
        """

        if not isinstance(
            player_input,
            str,
        ):
            raise TypeError(
                "player_input must be a string"
            )

        normalized_input = player_input.strip()

        if not normalized_input:
            raise CampaignTurnServiceError(
                "player_input must not be empty"
            )

        world = self.world_service.get_world()

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignTurnServiceError(
                "WorldService returned an invalid WorldState"
            )

        try:
            result = (
                self.turn_resolution_service.resolve_turn(
                    world,
                    normalized_input,
                )
            )

        except TurnResolutionServiceError as exc:
            raise CampaignTurnServiceError(
                "turn resolution failed"
            ) from exc

        except Exception as exc:
            raise CampaignTurnServiceError(
                "unexpected error while resolving turn"
            ) from exc

        if not isinstance(
            result,
            TurnResolutionResult,
        ):
            raise CampaignTurnServiceError(
                "TurnResolutionService returned "
                "an invalid TurnResolutionResult"
            )

        return result


    # ============================================================
    # CAMPAIGN STATE
    # ============================================================

    def load(self) -> WorldState:
        """
        Carga la campaña desde persistencia.

        Devuelve el WorldState cargado.
        """

        try:
            world = self.world_service.load()

        except Exception as exc:
            raise CampaignTurnServiceError(
                "failed to load campaign world"
            ) from exc

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignTurnServiceError(
                "WorldService returned an invalid WorldState"
            )

        return world

    def save(self) -> None:
        """
        Persiste explícitamente el estado actual de la campaña.
        """

        try:
            self.world_service.save()

        except Exception as exc:
            raise CampaignTurnServiceError(
                "failed to save campaign world"
            ) from exc

    def get_world(self) -> WorldState:
        """
        Devuelve el WorldState actual de la campaña.
        """

        world = self.world_service.get_world()

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignTurnServiceError(
                "WorldService returned an invalid WorldState"
            )

        return world