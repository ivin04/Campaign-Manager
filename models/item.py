from dataclasses import dataclass
from typing import Optional


@dataclass
class Item:
    """
    Definición de un tipo de objeto.

    Ejemplo:
        Diamante arcoíris

    Esta clase NO representa una copia física concreta.
    """

    id: Optional[int] = None

    name: str = ""

    description: str = ""

    significance: str = ""

    unique: bool = False

    notes: str = ""


@dataclass
class ItemInstance:
    """
    Copia física concreta de un Item.

    Ejemplo:

        Item:
            Diamante arcoíris

        Instances:
            #1 -> Fungoso
            #2 -> Templo perdido
    """

    id: Optional[int] = None

    item_id: int = 0

    instance_number: int = 1

    owner_id: Optional[int] = None

    location_id: Optional[int] = None

    condition: str = ""

    notes: str = ""

    active: bool = True