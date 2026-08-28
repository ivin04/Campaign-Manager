from __future__ import annotations

from dataclasses import dataclass

from models.campaign_state import CampaignState
from models.character_state import CharacterState
from models.session_state import SessionState
from models.world_state import WorldState

@dataclass(frozen=True)
class TurnContext:
    """
    Estado completo utilizado para resolver un turno.

    Contiene:

    - campaña actual
    - sesión actual
    - personaje activo
    - WorldState actual

    TurnContext es inmutable y no modifica ninguno
    de los objetos que contiene.
    """

    campaign: CampaignState
    current_session: SessionState | None
    active_character: CharacterState | None
    world: WorldState

    def __post_init__(self) -> None:
        if not isinstance(
            self.campaign,
            CampaignState,
        ):
            raise TypeError(
                "campaign must be a CampaignState"
            )

        if (
            self.current_session is not None
            and not isinstance(
                self.current_session,
                SessionState,
            )
        ):
            raise TypeError(
                "current_session must be a SessionState or None"
            )

        if (
            self.active_character is not None
            and not isinstance(
                self.active_character,
                CharacterState,
            )
        ):
            raise TypeError(
                "active_character must be a CharacterState or None"
            )

        if not isinstance(
            self.world,
            WorldState,
        ):
            raise TypeError(
                "world must be a WorldState"
            )