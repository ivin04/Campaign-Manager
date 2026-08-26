from typing import Optional

from pydantic import BaseModel


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    system: Optional[str] = None
    tone: Optional[str] = None
    summary: Optional[str] = None


class CampaignSessionUpdate(BaseModel):
    session_id: int | None = None


class SessionIn(BaseModel):
    number: int
    title: str = ""
    summary: str = ""
    start_location: str = ""
    end_location: str = ""
    notes: str = ""