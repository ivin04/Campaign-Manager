from dataclasses import dataclass
from typing import Any


@dataclass
class CreateRelationOperation:
    relation_id: str
    subject_id: int | str
    relation_type: str
    target_id: int | str
    metadata: dict[str, Any] | None = None


@dataclass
class UpdateRelationOperation:
    relation_id: str

    relation_type: str | None = None

    target_id: int | str | None = None

    metadata: dict[str, Any] | None = None

    active: bool | None = None


@dataclass
class RemoveRelationOperation:
    relation_id: str