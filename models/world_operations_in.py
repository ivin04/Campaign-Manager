from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorldOperationsIn(BaseModel):
    """
    Payload recibido desde SillyTavern.

    Ejemplo:

    {
        "operations": [
            {
                "type": "create_relation",
                "relation_id": "fungoso-goblin",
                "subject_id": "1",
                "relation_type": "enemy_of",
                "target_id": "2",
                "metadata": {
                    "reason": "Intentó robarle"
                }
            }
        ]
    }
    """

    operations: list[dict[str, Any]] = Field(default_factory=list)