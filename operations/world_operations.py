from dataclasses import dataclass
from typing import Any


# ============================================================
# BASE
# ============================================================

@dataclass(frozen=True)
class WorldOperation:
    """
    Operación de dominio que describe un cambio que debe
    realizarse sobre el estado de la campaña.

    Esta clase sirve como contrato conceptual.
    Las operaciones concretas de abajo contienen los datos
    específicos de cada cambio.
    """

    pass


# ============================================================
# ENTITIES
# ============================================================

@dataclass(frozen=True)
class CreateEntityOperation(WorldOperation):
    """
    Crea una entidad persistente dentro del mundo.

    El ID se genera por WorldApplier a partir del estado actual.
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
    Modifica únicamente los campos proporcionados de una entidad
    existente.

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
class TransferItemOperation(WorldOperation):
    """
    Transfiere una instancia física concreta de un objeto
    a otro propietario.

    El ItemInstance ya debe existir en WorldState.
    """

    instance_id: int
    new_owner_id: int


# ============================================================
# RESOURCES
# ============================================================

@dataclass(frozen=True)
class GainResourceOperation(WorldOperation):
    """
    Añade una cantidad de un recurso al balance
    de una entidad.
    """

    resource_id: int
    owner_id: int
    amount: float


@dataclass(frozen=True)
class SpendResourceOperation(WorldOperation):
    """
    Reduce una cantidad de un recurso que posee
    una entidad.
    """

    resource_id: int
    owner_id: int
    amount: float


@dataclass(frozen=True)
class TransferResourceOperation(WorldOperation):
    """
    Transfiere una cantidad de un recurso desde una entidad
    hacia otra.
    """

    resource_id: int
    source_id: int
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