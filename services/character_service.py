from models.character_state import CharacterState
from repositories.character_repository import (
    CharacterRepository,
)


class CharacterServiceError(Exception):
    pass


class CharacterService:

    def __init__(
        self,
        character_repository: CharacterRepository,
    ):
        self.character_repository = (
            character_repository
        )

    def change_hp(
        self,
        entity_id: int,
        amount: int,
    ) -> CharacterState:

        character = (
            self.character_repository.get_character(
                entity_id
            )
        )

        if character is None:
            raise CharacterServiceError(
                f"Character {entity_id} not found"
            )

        new_hp = character.current_hp + amount

        new_hp = max(
            0,
            min(
                new_hp,
                character.max_hp,
            ),
        )

        updated = CharacterState(
            entity_id=character.entity_id,
            level=character.level,
            class_name=character.class_name,
            current_hp=new_hp,
            max_hp=character.max_hp,
            armor_class=character.armor_class,
            strength=character.strength,
            dexterity=character.dexterity,
            constitution=character.constitution,
            intelligence=character.intelligence,
            wisdom=character.wisdom,
            charisma=character.charisma,
            proficiency_bonus=character.proficiency_bonus,
            metadata=dict(character.metadata),
        )

        try:
            return (
                self.character_repository.save_character(
                    updated
                )
            )

        except Exception as exc:
            raise CharacterServiceError(
                "failed to save character"
            ) from exc