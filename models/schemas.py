from typing import Optional

from pydantic import BaseModel


class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    system: Optional[str] = None
    tone: Optional[str] = None
    summary: Optional[str] = None


class CampaignSessionUpdate(BaseModel):
    session_id: int | None = None


class ItemIn(BaseModel):
    name: str
    description: str = ""
    owner: str = ""
    location: str = ""
    significance: str = ""
    notes: str = ""


class EventIn(BaseModel):
    title: str
    session: Optional[int] = None
    event_type: str = ""
    description: str
    consequences: str = ""
    secret: bool = False


class SessionIn(BaseModel):
    number: int
    title: str = ""
    summary: str = ""
    start_location: str = ""
    end_location: str = ""
    notes: str = ""