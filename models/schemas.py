from typing import Optional

from pydantic import BaseModel, Field


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    system: Optional[str] = None
    tone: Optional[str] = None
    summary: Optional[str] = None


class CampaignSessionUpdate(BaseModel):
    session_id: int | None = None


class SessionIn(BaseModel):
    number: int = Field(
        ...,
        ge=1,
    )
    title: str = ""
    summary: str = ""
    start_location: str = ""
    end_location: str = ""
    notes: str = ""


class TurnIn(BaseModel):
    player_input: str = Field(
        ...,
        min_length=1,
    )

class ActiveCharacterUpdate(BaseModel):
    character_id: int | None = Field(
        default=None,
        ge=1,
    )