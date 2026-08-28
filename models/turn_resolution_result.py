from __future__ import annotations

from dataclasses import dataclass

from operations.character_operations import (
    CharacterOperation,
)
from operations.world_operations import WorldOperation

from models.operation_result import (
    OperationStatus,
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
        Indica si el turno produjo algún cambio confirmado.

        Incluye tanto operaciones del mundo como operaciones
        del personaje.

        La aplicación de operaciones es atómica:
        si falta algún resultado o alguna operación falla,
        el turno no se considera cambiado.
        """

        if self.operation_count == 0:
            return False

        if (
            len(self.operation_results)
            != self.operation_count
        ):
            return False

        return any(
            self._result_changed(result)
            for result in self.operation_results
        )


    @staticmethod
    def _result_changed(result) -> bool:
        """
        Obtiene si un resultado representa un cambio.

        Soporta tanto OperationResult como los diccionarios
        utilizados actualmente por CharacterApplier.
        """

        if isinstance(result, dict):
            return bool(
                result.get(
                    "changed",
                    False,
                )
            )

        return bool(
            getattr(
                result,
                "changed",
                False,
            )
        )

    @property
    def all_operations_succeeded(self) -> bool:
        """
        Indica si todas las operaciones detectadas
        fueron aplicadas correctamente.

        La ausencia de resultados para alguna operación
        implica que el turno no se considera completamente
        exitoso.
        """

        if len(self.operation_results) != self.operation_count:
            return False

        return all(
            self._result_success(result)
            for result in self.operation_results
        )

    @property
    def operation_count(self) -> int:
        """
        Número total de operaciones detectadas.

        Incluye mundo y personaje.
        """

        return (
            len(self.operations)
            + len(self.character_operations)
        )

    @property
    def successful_operation_count(self) -> int:
        """
        Número de operaciones aplicadas correctamente.
        """

        return sum(
            self._result_success(result)
            for result in self.operation_results
        )

    @property
    def failed_operation_count(self) -> int:
        """
        Número de operaciones que no se aplicaron correctamente.
        """

        return sum(
            not self._result_success(result)
            for result in self.operation_results
        )

    @property
    def response(self) -> str:
        """
        Alias semántico para la narrativa.
        """

        return self.narrative

    @staticmethod
    def _result_success(result) -> bool:
        """
        Obtiene success tanto de OperationResult como
        de los resultados devueltos por los appliers
        que utilizan diccionarios.
        """

        if isinstance(result, dict):
            return bool(
                result.get("success", False)
            )

        return bool(
            getattr(result, "success", False)
        )