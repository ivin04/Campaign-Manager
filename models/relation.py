from dataclasses import dataclass
from typing import Any


@dataclass
class Relation:
    id: str

    subject_id: int
    relation_type: str
    target_id: int

    metadata: dict[str, Any] | None = None

    active: bool = True