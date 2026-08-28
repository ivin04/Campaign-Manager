from __future__ import annotations

from dataclasses import dataclass

from operations.character_operations import (
    CharacterOperation,
)
from operations.world_operations import WorldOperation

from operations.character_operations import (
    CharacterOperation,
)


@dataclass(frozen=True)
class TurnResolutionResult:
    """
    Resultado completo de la resolución de un turno.

    Contiene:

    - entrada del jugador
    - narrativa generada por el DM
    - operaciones detectadas por el extractor
    - resultado de aplicar las operaciones

    El resultado es inmutable.

    La aplicación de operaciones es atómica:

        - si todas las operaciones tienen éxito,
          el cambio del mundo se considera confirmado.

        - si una operación falla,
          el WorldState original se conserva.
    """

    player_input: str
    narrative: str

    operations: tuple[WorldOperation, ...] = ()

    character_operations: tuple[
        CharacterOperation,
        ...
    ] = ()

    operation_results: tuple = ()

    @property
    def world_changed(self) -> bool:
        """
        Indica si el turno produjo un cambio confirmado
        en el WorldState.

        La aplicación de operaciones es atómica:
        si una sola operación falla, el lote completo
        se considera no confirmado y el WorldState original
        permanece intacto.
        """

        if not self.operations:
            return False

        if len(self.operation_results) != len(self.operations):
            return False

        return all(
            result.changed
            for result in self.operation_results
        )

    @property
    def all_operations_succeeded(self) -> bool:
        """
        Indica si todas las operaciones fueron aplicadas
        correctamente.

        Un turno sin operaciones se considera exitoso
        respecto a la aplicación.
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