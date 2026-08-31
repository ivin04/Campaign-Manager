from models.operation_result import (
    OperationResult,
    OperationStatus,
)

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
        self.character_service = (
            character_service
        )

    def apply(
        self,
        operation,
        *,
        conn=None,
    ) -> OperationResult:

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
                message = str(exc)

                if "not found" in message.lower():
                    status = OperationStatus.NOT_FOUND
                else:
                    status = OperationStatus.INVALID

                return OperationResult(
                    status=status,
                    message=message,
                    operation=operation,
                    data={
                        "entity_id": operation.entity_id,
                    },
                )

            return OperationResult(
                status=OperationStatus.SUCCESS,
                message="Character HP changed",
                operation=operation,
                data={
                    "entity_id": operation.entity_id,
                    "current_hp": character.current_hp,
                },
            )

        raise CharacterApplierError(
            f"unsupported character operation: "
            f"{type(operation).__name__}"
        )