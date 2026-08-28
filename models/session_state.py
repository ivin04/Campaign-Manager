from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SessionState:
    """
    Estado persistente de una sesión de campaña.

    Una sesión representa una unidad de juego dentro de la campaña.
    No contiene el WorldState ni el estado mecánico del personaje.
    """

    session_id: int | None = None
    number: int = 0
    title: str = ""
    summary: str = ""
    start_location: str = ""
    end_location: str = ""
    notes: str = ""