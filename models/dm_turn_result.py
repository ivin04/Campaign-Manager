from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DMTurnResult:
    """
    Resultado inmutable de un turno del Dungeon Master.

    Representa exclusivamente el resultado narrativo del turno.
    Las mutaciones persistentes del mundo se gestionan fuera de
    esta capa.
    """

    player_input: str
    narrative: str
    context: str = ""

    @property
    def response(self) -> str:
        """
        Alias semántico para la respuesta narrativa.
        """
        return self.narrative