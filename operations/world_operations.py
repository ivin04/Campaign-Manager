from dataclasses import dataclass
from typing import Any

from operations.operation_reference import OperationReference


# ============================================================
# BASE
# ============================================================

@dataclass(frozen=True)
class WorldOperation:
    """
    Operación de dominio que describe un cambio que debe
    realizarse sobre el estado de la campaña.

    Las operaciones concretas contienen los datos
    necesarios para realizar cada cambio.
    """

    pass


# ============================================================
# ENTITIES
# ============================================================

@dataclass(frozen=True)
class CreateEntityOperation(WorldOperation):
    """
    Crea una entidad persistente dentro del mundo.

    El ID se genera por WorldApplier.
    El LLM NO debe proporcionar el ID.
    """

    name: str
    entity_type: str = ""
    description: str = ""
    notes: str = ""
    active: bool = True


@dataclass(frozen=True)
class UpdateEntityOperation(WorldOperation):
    """
    Modifica únicamente los campos proporcionados de una
    entidad existente.

    None significa "no modificar ese campo".
    """

    entity_id: int

    name: str | None = None
    entity_type: str | None = None
    description: str | None = None
    notes: str | None = None
    active: bool | None = None


# ============================================================
# ITEMS
# ============================================================

@dataclass(frozen=True)
class CreateItemOperation(WorldOperation):
    """
    Crea la definición de un tipo de objeto.

    Ejemplo:

        Item:
            Espada de hierro

    Esto NO crea una copia física concreta.
    """

    name: str
    description: str = ""
    significance: str = ""
    unique: bool = False
    notes: str = ""


@dataclass(frozen=True)
class CreateItemInstanceOperation(WorldOperation):
    """
    Crea una instancia física concreta de un Item existente.

    Ejemplo:

        Item:
            Espada de hierro

        Instance:
            #1 -> Fungoso
    """

    item_id: int | OperationReference
    instance_number: int = 1
    owner_id: int | None = None
    location_id: int | None = None
    condition: str = ""
    notes: str = ""
    active: bool = True


@dataclass(frozen=True)
class TransferItemOperation(WorldOperation):
    """
    Transfiere una instancia física concreta de un objeto
    a otro propietario.

    La instancia ya debe existir.
    """

    instance_id: int | OperationReference
    new_owner_id: int


# ============================================================
# RESOURCES
# ============================================================

@dataclass(frozen=True)
class CreateResourceOperation(WorldOperation):
    """
    Crea un recurso cuantificable de la campaña.

    Ejemplos:

        oro
        reputación
        suministros
        influencia
    """

    name: str
    resource_type: str = "generic"
    unit: str = ""
    notes: str = ""


@dataclass(frozen=True)
class GainResourceOperation(WorldOperation):
    """
    Añade una cantidad de un recurso al balance
    de una entidad.
    """

    resource_id: int | OperationReference
    owner_id: int
    amount: float


@dataclass(frozen=True)
class SpendResourceOperation(WorldOperation):
    """
    Reduce una cantidad de un recurso que posee
    una entidad.
    """

    resource_id: int | OperationReference
    owner_id: int
    amount: float


@dataclass(frozen=True)
class TransferResourceOperation(WorldOperation):
    """
    Transfiere una cantidad de un recurso desde una entidad
    hacia otra.
    """

    resource_id: int | OperationReference
    subject_id: int
    target_id: int
    amount: float


# ============================================================
# RELATIONS
# ============================================================

@dataclass(frozen=True)
class CreateRelationOperation(WorldOperation):
    """
    Crea una relación entre dos entidades existentes.
    """

    relation_id: str
    subject_id: int
    relation_type: str
    target_id: int
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class UpdateRelationOperation(WorldOperation):
    """
    Modifica una relación existente.
    """

    relation_id: str

    relation_type: str | None = None

    target_id: int | None = None

    metadata: dict[str, Any] | None = None

    active: bool | None = None


@dataclass(frozen=True)
class RemoveRelationOperation(WorldOperation):
    """
    Desactiva una relación existente.
    """

    relation_id: str


# ============================================================
# EVENTS
# ============================================================

@dataclass(frozen=True)
class CreateEventOperation(WorldOperation):
    """
    Crea un evento histórico en el mundo.
    """

    event_id: str

    event_type: str

    title: str

    description: str = ""

    consequences: str = ""

    session_id: int | None = None

    secret: bool = False

    metadata: dict[str, Any] | None = None