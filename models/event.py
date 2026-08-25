from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    id: str

    event_type: str
    title: str

    description: str = ""
    consequences: str = ""

    session_id: int | None = None

    secret: bool = False

    metadata: dict[str, Any] = field(default_factory=dict)