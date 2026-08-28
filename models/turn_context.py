from __future__ import annotations

from dataclasses import dataclass

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

    campaign: object
    current_session: object | None
    active_character: object | None
    world: WorldState

    def __post_init__(self) -> None:
        if not isinstance(
            self.world,
            WorldState,
        ):
            raise TypeError(
                "world must be a WorldState"
            )