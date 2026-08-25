from dataclasses import dataclass
from typing import Any


@dataclass
class Relation:
    id: str

    subject_id: str
    relation_type: str
    target_id: str

    metadata: dict[str, Any] | None = None

    active: bool = True