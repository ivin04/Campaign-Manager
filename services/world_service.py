from models.world_state import WorldState
from models.operation_result import OperationResult
from repositories.world_repository import WorldRepository
from services.world_applier import WorldApplier


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

    def apply_and_save(
        self,
        operation,
    ) -> OperationResult:
        """
        Aplica una operación y persiste el mundo únicamente
        si la operación ha tenido éxito.
        """

        result = self.apply(operation)

        if not result.success:
            return result

        self.save()

        return result

    def get_world(self) -> WorldState:
        """
        Devuelve el estado actual del mundo.
        """

        return self.world