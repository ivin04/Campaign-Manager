from dataclasses import dataclass, field
from typing import Any


@dataclass
class CharacterState:
    """
    Mechanical state for a D&D 5e (2014) character.

    Identity and narrative information belong to Entity.
    CharacterState contains only game-mechanical data.
    """

    entity_id: int

    level: int = 1
    class_name: str | None = None

    current_hp: int = 0
    max_hp: int = 0

    armor_class: int = 10

    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    proficiency_bonus: int = 2

    metadata: dict[str, Any] = field(default_factory=dict)