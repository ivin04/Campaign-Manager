from models.world_state import WorldState
from models.operation_result import OperationResult
from repositories.world_repository import WorldRepository
from services.world_applier import WorldApplier

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
    ):
        """
        Aplica varias operaciones de forma atómica a nivel de WorldState.

        Comportamiento:

        - Las operaciones se aplican sobre una copia.
        - Si una operación devuelve success=False, se aborta todo.
        - Si una operación lanza una excepción, se aborta todo.
        - El WorldState original no se modifica si algo falla.
        - NO persiste el estado en SQLite.

        Devuelve:

            {
                "success": True/False,
                "results": [...]
            }

        Si todas las operaciones tienen éxito, el nuevo WorldState
        queda establecido en memoria.
        """

        # =========================================================
        # 1. Guardar el estado original
        # =========================================================

        original_state = self.world

        # =========================================================
        # 2. Crear estado de trabajo independiente
        # =========================================================

        working_state = copy.deepcopy(
            original_state
        )

        self.world = working_state

        results = []

        try:

            # =====================================================
            # 3. Aplicar TODAS las operaciones sobre la copia
            # =====================================================

            for operation in operations:

                result = self.apply(
                    operation
                )

                results.append(result)

                # -------------------------------------------------
                # Si una operación falla lógicamente:
                # abortamos TODO.
                # -------------------------------------------------

                if not result.success:

                    self.world = original_state

                    return {
                        "success": False,
                        "results": results,
                    }

            # =====================================================
            # 4. Todas las operaciones han tenido éxito
            # =====================================================

            return {
                "success": True,
                "results": results,
                "world": self.world,
            }

        except Exception:

            # =====================================================
            # 5. Error inesperado
            # =====================================================

            self.world = original_state

            raise

    def apply_operations_and_save(
        self,
        operations,
    ):
        """
        Aplica varias operaciones de forma atómica a nivel de WorldState.

        Comportamiento:

        - Las operaciones se aplican sobre una copia.
        - Si una operación devuelve success=False, se aborta todo.
        - Si una operación lanza una excepción, se aborta todo.
        - El WorldState original no se modifica si algo falla.
        - Solo se persiste una vez cuando todas las operaciones tienen éxito.

        NOTA:
        La atomicidad de SQLite se garantiza en el repositorio.
        Este método garantiza la atomicidad del WorldState en memoria.
        """

        # =========================================================
        # 1. Guardar el estado original
        # =========================================================

        original_state = self.world

        # =========================================================
        # 2. Crear estado de trabajo independiente
        # =========================================================

        working_state = copy.deepcopy(
            original_state
        )

        self.world = working_state

        results = []

        try:

            # =====================================================
            # 3. Aplicar TODAS las operaciones sobre la copia
            # =====================================================

            for operation in operations:

                result = self.apply(
                    operation
                )

                results.append(result)

                # -------------------------------------------------
                # Si una operación falla lógicamente:
                # abortamos TODO.
                # -------------------------------------------------

                if not result.success:

                    self.world = original_state

                    return {
                        "success": False,
                        "results": results,
                    }

            # =====================================================
            # 4. Todas las operaciones han tenido éxito
            # =====================================================

            self.save()

            return {
                "success": True,
                "results": results,
                "world": self.world,
            }

        except Exception:

            # =====================================================
            # 5. Error inesperado
            # =====================================================

            self.world = original_state

            raise

    def get_world(self) -> WorldState:
        """
        Devuelve el estado actual del mundo.
        """

        return self.world