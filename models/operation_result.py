from dataclasses import dataclass
from enum import Enum
from typing import Any


class OperationStatus(str, Enum):
    SUCCESS = "success"
    NOT_FOUND = "not_found"
    INVALID = "invalid"
    DUPLICATE = "duplicate"
    NO_CHANGE = "no_change"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class OperationResult:
    status: OperationStatus
    message: str = ""
    operation: Any | None = None
    data: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        return self.status in (
            OperationStatus.SUCCESS,
            OperationStatus.NO_CHANGE,
        )

    @property
    def changed(self) -> bool:
        """
        Indica si la operación produjo una modificación real
        del estado.
        """

        return self.status == OperationStatus.SUCCESS