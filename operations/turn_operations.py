from typing import TypeAlias

from operations.world_operations import WorldOperation
from operations.character_operations import CharacterOperation


TurnOperation: TypeAlias = (
    WorldOperation
    | CharacterOperation
)