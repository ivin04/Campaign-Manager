from __future__ import annotations

from dataclasses import dataclass

from models.world_state import WorldState

from repositories.campaign_repository import CampaignRepository
from repositories.character_repository import CharacterRepository

from services.world_service import WorldService


class CampaignStateServiceError(RuntimeError):
    """
    Error base del servicio de estado de campaña.
    """


@dataclass(frozen=True)
class CampaignState:
    """
    Estado operativo completo de una campaña.

    Contiene únicamente referencias al estado persistido
    y el WorldState actual.

    No modifica ninguno de ellos.
    """

    campaign: object
    current_session: object | None
    active_character: object | None
    world: WorldState


class CampaignStateService:
    """
    Ensambla el estado completo necesario para ejecutar la campaña.

    Responsabilidad:

        CampaignRepository
              |
              +--> campaign
              +--> current session
              +--> active character id
                    |
                    v
              CharacterRepository
                    |
                    v
              active character

        WorldService
              |
              v
          WorldState

                    ↓

             CampaignState

    Este servicio NO:
        - genera narrativa
        - resuelve turnos
        - aplica operaciones
        - modifica WorldState
        - accede directamente a SQLite

    Su única responsabilidad es ensamblar el estado actual.
    """

    def __init__(
        self,
        *,
        campaign_repository: CampaignRepository,
        character_repository: CharacterRepository,
        world_service: WorldService,
    ) -> None:

        if not isinstance(
            campaign_repository,
            CampaignRepository,
        ):
            raise TypeError(
                "campaign_repository must be a CampaignRepository"
            )

        if not isinstance(
            character_repository,
            CharacterRepository,
        ):
            raise TypeError(
                "character_repository must be a CharacterRepository"
            )

        if not isinstance(
            world_service,
            WorldService,
        ):
            raise TypeError(
                "world_service must be a WorldService"
            )

        self.campaign_repository = campaign_repository
        self.character_repository = character_repository
        self.world_service = world_service

    # ============================================================
    # PUBLIC API
    # ============================================================

    def get_state(
        self,
        campaign_id: int = 1,
    ) -> CampaignState:
        """
        Devuelve el estado completo actual de la campaña.
        """

        campaign = self.campaign_repository.get_campaign(
            campaign_id
        )

        if campaign is None:
            raise CampaignStateServiceError(
                "campaign does not exist"
            )

        current_session = (
            self.campaign_repository.get_current_session(
                campaign_id
            )
        )

        active_character_id = (
            self.campaign_repository.get_active_character_id(
                campaign_id
            )
        )

        active_character = None

        if active_character_id is not None:
            active_character = (
                self.character_repository.get_character(
                    active_character_id
                )
            )

            if active_character is None:
                raise CampaignStateServiceError(
                    "active character does not exist"
                )

        world = self.world_service.get_world()

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignStateServiceError(
                "WorldService returned an invalid WorldState"
            )

        return CampaignState(
            campaign=campaign,
            current_session=current_session,
            active_character=active_character,
            world=world,
        )

    # ============================================================
    # ACTIVE CHARACTER
    # ============================================================

    def set_active_character(
        self,
        character_id: int | None,
        campaign_id: int = 1,
    ) -> CampaignState:
        """
        Establece o elimina el personaje activo.

        Si se proporciona un ID, el personaje debe existir.
        """

        if character_id is not None:

            character = (
                self.character_repository.get_character(
                    character_id
                )
            )

            if character is None:
                raise CampaignStateServiceError(
                    "cannot activate a character that does not exist"
                )

        self.campaign_repository.update_active_character(
            campaign_id=campaign_id,
            character_id=character_id,
        )

        return self.get_state(campaign_id)

    # ============================================================
    # CURRENT SESSION
    # ============================================================

    def set_current_session(
        self,
        session_id: int | None,
        campaign_id: int = 1,
    ) -> CampaignState:
        """
        Establece o elimina la sesión actual.

        Si se proporciona un ID, la sesión debe existir.
        """

        if session_id is not None:

            session = (
                self.campaign_repository.get_session(
                    session_id
                )
            )

            if session is None:
                raise CampaignStateServiceError(
                    "cannot activate a session that does not exist"
                )

        self.campaign_repository.update_current_session(
            campaign_id=campaign_id,
            session_id=session_id,
        )

        return self.get_state(campaign_id)

    # ============================================================
    # WORLD
    # ============================================================

    def get_world(
        self,
    ) -> WorldState:
        """
        Devuelve únicamente el WorldState actual.
        """

        world = self.world_service.get_world()

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignStateServiceError(
                "WorldService returned an invalid WorldState"
            )

        return world

    def load_world(
        self,
    ) -> WorldState:
        """
        Carga el WorldState desde persistencia.
        """

        try:
            world = self.world_service.load()

        except Exception as exc:
            raise CampaignStateServiceError(
                "failed to load campaign world"
            ) from exc

        if not isinstance(
            world,
            WorldState,
        ):
            raise CampaignStateServiceError(
                "WorldService returned an invalid WorldState"
            )

        return world

    def save_world(
        self,
    ) -> None:
        """
        Persiste explícitamente el WorldState actual.
        """

        try:
            self.world_service.save()

        except Exception as exc:
            raise CampaignStateServiceError(
                "failed to save campaign world"
            ) from exc
