from __future__ import annotations

from models.dm_turn_result import DMTurnResult
from models.world_state import WorldState
from services.dm_service import DMService


class DMTurnServiceError(RuntimeError):
    """Error base del servicio de turnos del Dungeon Master."""


class DMTurnService:
    """
    Orquesta un turno completo del Dungeon Master.

    Responsabilidades:

    - Validar WorldState.
    - Validar la entrada del jugador.
    - Delegar la generación narrativa a DMService.
    - Devolver un DMTurnResult.

    NO debe:

    - modificar WorldState.
    - ejecutar WorldOperation.
    - persistir memoria.
    - acceder a SQLite.
    - conocer Ollama.
    - conocer el modelo LLM.
    - interpretar operaciones generadas por el LLM.

    Esta clase es deliberadamente fina.

    DMService sigue siendo responsable de:

        contexto -> prompt -> LLM -> narrativa

    DMTurnService añade la semántica de "turno":
    
        input jugador -> resultado de turno
    """

    def __init__(
        self,
        dm_service: DMService,
    ) -> None:

        if not isinstance(dm_service, DMService):
            raise TypeError(
                "dm_service must be a DMService"
            )

        self.dm_service = dm_service

    # ============================================================
    # PUBLIC API
    # ============================================================

    def run_turn(
        self,
        world: WorldState,
        player_input: str,
    ) -> DMTurnResult:
        """
        Ejecuta un turno narrativo completo.

        WorldState nunca se modifica.
        """

        self._validate_world(world)

        normalized_input = self._validate_player_input(
            player_input
        )

        if not normalized_input:
            raise DMTurnServiceError(
                "player_input must not be empty"
            )

        try:
            narrative = self.dm_service.generate(
                world,
                normalized_input,
            )
        except Exception as exc:
            if isinstance(exc, DMTurnServiceError):
                raise

            raise DMTurnServiceError(
                "DMService failed to generate the turn"
            ) from exc

        if not isinstance(narrative, str):
            raise DMTurnServiceError(
                "DMService returned a non-string narrative"
            )

        narrative = narrative.strip()

        if not narrative:
            raise DMTurnServiceError(
                "DMService returned an empty narrative"
            )

        return DMTurnResult(
            player_input=normalized_input,
            narrative=narrative,
        )

    def __call__(
        self,
        world: WorldState,
        player_input: str,
    ) -> DMTurnResult:
        """
        Permite utilizar DMTurnService como callable.
        """

        return self.run_turn(
            world,
            player_input,
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