from operations.character_operations import (
    ChangeCharacterHpOperation,
)
from services.character_service import (
    CharacterService,
    CharacterServiceError,
)


class CharacterApplierError(Exception):
    pass


class CharacterApplier:

    def __init__(
        self,
        character_service: CharacterService,
    ):
        self.character_service = character_service

    def apply(
        self,
        operation,
        *,
        conn=None,
    ):
        if isinstance(
            operation,
            ChangeCharacterHpOperation,
        ):
            try:
                if conn is None:
                    character = (
                        self.character_service.change_hp(
                            entity_id=operation.entity_id,
                            amount=operation.amount,
                        )
                    )
                else:
                    character = (
                        self.character_service.change_hp(
                            entity_id=operation.entity_id,
                            amount=operation.amount,
                            conn=conn,
                        )
                    )

            except CharacterServiceError as exc:
                raise CharacterApplierError(
                    str(exc)
                ) from exc

            return {
                "success": True,
                "changed": True,
                "entity_id": operation.entity_id,
                "current_hp": character.current_hp,
            }

        raise CharacterApplierError(
            f"unsupported character operation: "
            f"{type(operation).__name__}"
        )