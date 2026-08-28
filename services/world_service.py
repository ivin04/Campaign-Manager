from models.world_state import WorldState
from models.operation_result import OperationResult
from repositories.world_repository import WorldRepository
from services.world_applier import WorldApplier

from models.world_application_result import (
    WorldApplicationResult,
)

import copy

class WorldService:
    """
    Fachada principal para trabajar con el estado persistente del mundo.

    Responsabilidades:

    - Cargar el mundo desde el repositorio.
    - Mantener el WorldState en memoria.
    - Aplicar operaciones mediante WorldApplier.
    - Persistir el estado mediante WorldRepository.

    WorldService NO contiene la lógica específica de cada operación.
    """

    def __init__(
        self,
        repository: WorldRepository | None = None,
        applier: WorldApplier | None = None,
    ):
        self.repository = repository or WorldRepository()
        self.applier = applier or WorldApplier()

        self.world = WorldState()

    def load(self) -> WorldState:
        """
        Carga el mundo desde SQLite y lo establece como estado actual.
        """

        self.world = self.repository.load_world()

        return self.world

    def save(self) -> None:
        """
        Persiste el estado actual del mundo.
        """

        self.repository.save_world(self.world)

    def apply(
        self,
        operation,
    ) -> OperationResult:
        """
        Aplica una operación al mundo en memoria.

        No guarda automáticamente en SQLite.

        Devuelve el OperationResult producido por WorldApplier.
        """

        return self.applier.apply(
            self.world,
            operation,
        )

    def apply_operations(
        self,
        operations,
    ) -> WorldApplicationResult:
        """
        Aplica varias operaciones de forma atómica sobre WorldState.

        Las operaciones se aplican sobre una copia.

        Si alguna operación falla:

            - se descarta el estado de trabajo
            - se conserva el WorldState original
            - changed=False
            - no se persiste nada

        Si todas tienen éxito:

            - el nuevo WorldState pasa a ser el estado actual
            - changed=True si hubo operaciones
        """

        original_state = self.world

        working_state = copy.deepcopy(
            original_state
        )

        self.world = working_state

        results = []

        try:

            for operation in operations:

                result = self.apply(
                    operation
                )

                results.append(result)

                if not result.success:

                    self.world = original_state

                    return WorldApplicationResult(
                        success=False,
                        changed=False,
                        results=tuple(results),
                        world=original_state,
                    )

            changed = bool(results)

            return WorldApplicationResult(
                success=True,
                changed=changed,
                results=tuple(results),
                world=self.world,
            )

        except Exception:

            self.world = original_state

            raise

    def apply_operations_and_save(
        self,
        operations,
    ) -> WorldApplicationResult:
        """
        Aplica operaciones de forma atómica y persiste únicamente
        si el WorldState ha cambiado realmente.

        Reglas:

            0 operaciones
                -> success=True
                -> changed=False
                -> NO guarda

            todas SUCCESS
                -> success=True
                -> changed=True
                -> guarda una vez

            alguna falla
                -> success=False
                -> changed=False
                -> NO guarda

            error durante persistencia
                -> restaura la referencia original en memoria
                -> propaga la excepción
        """

        original_world = self.world

        result = self.apply_operations(
            operations
        )

        if not result.success:
            return result

        if not result.changed:
            return result

        try:
            self.save()

        except Exception:
            self.world = original_world
            raise

        return result

    def get_world(self) -> WorldState:
        """
        Devuelve el estado actual del mundo.
        """

        return self.world