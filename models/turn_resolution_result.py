from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.operation_result import OperationResult
from operations.world_operations import WorldOperation


@dataclass(frozen=True)
class TurnResolutionResult:
    """
    Resultado completo de la resolución de un turno.

    Contiene:

    - entrada original del jugador
    - narrativa generada por el DM
    - operaciones detectadas por el extractor
    - resultado de aplicar cada operación
    - contexto utilizado para generar la narrativa

    El modelo es inmutable.

    La mutación del WorldState ocurre exclusivamente a través de
    WorldApplier.
    """

    player_input: str
    narrative: str
    operations: tuple[WorldOperation, ...] = ()
    operation_results: tuple[OperationResult, ...] = ()
    context: str = ""

    @property
    def world_changed(self) -> bool:
        """
        Indica si al menos una operación modificó correctamente
        el estado del mundo.
        """

        return any(
            result.success
            for result in self.operation_results
        )

    @property
    def all_operations_succeeded(self) -> bool:
        """
        Indica si todas las operaciones fueron aplicadas
        correctamente.

        Un turno sin operaciones se considera exitoso.
        """

        return all(
            result.success
            for result in self.operation_results
        )

    @property
    def operation_count(self) -> int:
        """
        Número de operaciones detectadas.
        """

        return len(self.operations)

    @property
    def successful_operation_count(self) -> int:
        """
        Número de operaciones aplicadas correctamente.
        """

        return sum(
            result.success
            for result in self.operation_results
        )

    @property
    def failed_operation_count(self) -> int:
        """
        Número de operaciones que no se aplicaron correctamente.
        """

        return sum(
            not result.success
            for result in self.operation_results
        )

    @property
    def response(self) -> str:
        """
        Alias semántico para la narrativa.
        """

        return self.narrative