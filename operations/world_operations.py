from dataclasses import dataclass
from typing import Any


@dataclass
class WorldOperation:
    """
    Cambio concreto que debe aplicarse al estado de la campaña.
    """

    operation_type: str

    data: dict[str, Any]

OP_CREATE_ENTITY = "CREATE_ENTITY"
OP_UPDATE_ENTITY = "UPDATE_ENTITY"

OP_CREATE_ITEM = "CREATE_ITEM"
OP_CREATE_ITEM_INSTANCE = "CREATE_ITEM_INSTANCE"
OP_UPDATE_ITEM_INSTANCE = "UPDATE_ITEM_INSTANCE"

OP_CREATE_RESOURCE = "CREATE_RESOURCE"
OP_UPDATE_RESOURCE_BALANCE = "UPDATE_RESOURCE_BALANCE"

OP_CREATE_RELATION = "CREATE_RELATION"
OP_UPDATE_RELATION = "UPDATE_RELATION"

OP_CREATE_EVENT = "CREATE_EVENT"

@dataclass
class TransferItemOperation:
    """
    Transfiere una instancia concreta de un objeto
    desde su propietario actual a otro.
    """

    instance_id: int
    new_owner_id: int

@dataclass
class GainResourceOperation:
    """
    Añade una cantidad de un recurso al balance
    de una entidad.
    """

    resource_id: int
    owner_id: int
    amount: float

@dataclass
class SpendResourceOperation:
    """
    Reduce una cantidad de un recurso que posee una entidad.
    """

    resource_id: int
    owner_id: int
    amount: float

@dataclass
class TransferResourceOperation:
    """
    Transfiere una cantidad de un recurso
    desde una entidad a otra.
    """

    resource_id: int
    source_id: int
    target_id: int
    amount: float