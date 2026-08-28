from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CampaignState:
    """
    Estado de alto nivel de una campaña.

    No contiene directamente el estado interno del mundo.
    WorldState sigue siendo responsabilidad de WorldService.
    """

    campaign_id: int = 1
    name: str = ""
    system: str = "D&D 5e 2014"
    tone: str = ""
    current_location_id: int | None = None
    current_session_id: int | None = None
    active_character_id: int | None = None
    summary: str = ""