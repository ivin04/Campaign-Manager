from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TurnRecord:
    """
    Registro persistente de un turno de campaña.

    Contiene únicamente información histórica del turno.
    El WorldState continúa siendo la fuente de verdad del mundo.
    """

    id: int | None = None
    session_id: int | None = None

    player_input: str = ""
    narrative: str = ""

    operation_count: int = 0
    successful_operation_count: int = 0
    failed_operation_count: int = 0

    all_operations_succeeded: bool = True
    world_changed: bool = False

    created_at: str | None = None