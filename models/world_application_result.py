from __future__ import annotations

from dataclasses import dataclass

from models.operation_result import OperationResult
from models.world_state import WorldState


@dataclass(frozen=True)
class WorldApplicationResult:
    """
    Resultado de aplicar un conjunto de operaciones sobre el mundo.

    Representa exclusivamente el resultado de la capa WorldService.

    - success=True:
        todas las operaciones fueron aplicadas correctamente.

    - success=False:
        alguna operación falló y el estado original se conserva.

    - changed=True:
        el WorldState sufrió al menos una modificación confirmada.

    - changed=False:
        no hubo modificación confirmada.

    La persistencia no forma parte de este objeto.
    """

    success: bool
    changed: bool
    results: tuple[OperationResult, ...] = ()
    world: WorldState | None = None

    @property
    def operation_count(self) -> int:
        return len(self.results)

    @property
    def successful_operation_count(self) -> int:
        return sum(
            result.success
            for result in self.results
        )

    @property
    def failed_operation_count(self) -> int:
        return sum(
            not result.success
            for result in self.results
        )