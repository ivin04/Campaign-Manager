from dataclasses import dataclass

from operations.turn_operations import TurnOperation


@dataclass(frozen=True)
class ReferencedOperation:
    """
    Operación acompañada de una referencia opcional que permite
    a operaciones posteriores utilizar IDs generados por ella.
    """

    operation: TurnOperation
    ref: str | None = None