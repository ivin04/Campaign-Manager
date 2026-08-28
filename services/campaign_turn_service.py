from __future__ import annotations

from models.turn_resolution_result import TurnResolutionResult
from models.world_state import WorldState

from services.campaign_state_service import (
    CampaignState,
    CampaignStateService,
    CampaignStateServiceError,
)
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
    Fachada de alto nivel para ejecutar un turno de campaña.

    Arquitectura:

        CampaignTurnService
                |
                v
        CampaignStateService
                |
                +--> CampaignRepository
                +--> CharacterRepository
                +--> WorldService
                |
                v
          CampaignState
                |
                v
        TurnResolutionService

    CampaignTurnService coordina el flujo de campaña.

    No accede directamente a SQLite.

    CampaignStateService es la fachada para obtener y persistir
    el estado de campaña.
    """

    def __init__(
        self,
        *,
        turn_resolution_service: TurnResolutionService,
        world_service: WorldService,
        campaign_state_service: CampaignStateService | None = None,
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

        if campaign_state_service is not None and not isinstance(
            campaign_state_service,
            CampaignStateService,
        ):
            raise TypeError(
                "campaign_state_service must be a "
                "CampaignStateService"
            )

        self.turn_resolution_service = (
            turn_resolution_service
        )

        self.world_service = world_service

        self.campaign_state_service = (
            campaign_state_service
        )

    # ============================================================
    # PLAY TURN
    # ============================================================

    def play_turn(
        self,
        player_input: str,
    ) -> TurnResolutionResult:
        """
        Ejecuta un turno completo.

        Con CampaignStateService:

            1. obtiene el estado de campaña
            2. obtiene WorldState
            3. resuelve el turno
            4. devuelve el resultado

        Sin CampaignStateService se conserva el comportamiento
        anterior para compatibilidad.
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

        # --------------------------------------------------------
        # Obtener WorldState
        # --------------------------------------------------------

        if self.campaign_state_service is not None:

            try:
                state = (
                    self.campaign_state_service.get_state()
                )

            except CampaignStateServiceError as exc:
                raise CampaignTurnServiceError(
                    "failed to obtain campaign state"
                ) from exc

            except Exception as exc:
                raise CampaignTurnServiceError(
                    "CampaignStateService failed to get "
                    "campaign state"
                ) from exc

            if not isinstance(
                state,
                CampaignState,
            ):
                raise CampaignTurnServiceError(
                    "CampaignStateService returned an invalid "
                    "CampaignState"
                )

            world = state.world

        else:

            try:
                world = (
                    self.world_service.get_world()
                )

            except Exception as exc:
                raise CampaignTurnServiceError(
                    "WorldService failed to get world"
                ) from exc

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignTurnServiceError(
                "WorldService returned an invalid WorldState"
            )

        # --------------------------------------------------------
        # Resolver turno
        # --------------------------------------------------------

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
    # LOAD
    # ============================================================

    def load(self) -> WorldState:
        """
        Carga el WorldState persistido.

        CampaignStateService es la fachada principal.
        """

        if self.campaign_state_service is not None:

            try:
                world = (
                    self.campaign_state_service.load_world()
                )

            except CampaignStateServiceError as exc:
                raise CampaignTurnServiceError(
                    "failed to obtain campaign state"
                ) from exc

            except Exception as exc:
                raise CampaignTurnServiceError(
                    "failed to load campaign world"
                ) from exc

        else:

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

    # ============================================================
    # SAVE
    # ============================================================

    def save(self) -> None:
        """
        Persiste explícitamente el estado actual.

        CampaignStateService es la fachada principal.
        """

        if self.campaign_state_service is not None:

            try:
                self.campaign_state_service.save_world()

            except CampaignStateServiceError as exc:
                raise CampaignTurnServiceError(
                    "failed to save campaign world"
                ) from exc

            except Exception as exc:
                raise CampaignTurnServiceError(
                    "failed to save campaign world"
                ) from exc

            return

        try:
            self.world_service.save()

        except Exception as exc:
            raise CampaignTurnServiceError(
                "failed to save campaign world"
            ) from exc

    # ============================================================
    # GET WORLD
    # ============================================================

    def get_world(self) -> WorldState:
        """
        Devuelve el WorldState actual.

        Cuando existe CampaignStateService, delega en él.
        """

        if self.campaign_state_service is not None:

            try:
                world = (
                    self.campaign_state_service.get_world()
                )

            except CampaignStateServiceError as exc:
                raise CampaignTurnServiceError(
                    "failed to obtain campaign state"
                ) from exc

            except Exception as exc:
                raise CampaignTurnServiceError(
                    "CampaignStateService failed to get world"
                ) from exc

        else:

            try:
                world = (
                    self.world_service.get_world()
                )

            except Exception as exc:
                raise CampaignTurnServiceError(
                    "WorldService failed to get world"
                ) from exc

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignTurnServiceError(
                "WorldService returned an invalid WorldState"
            )

        return world