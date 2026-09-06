from dataclasses import dataclass


@dataclass
class Resource:
    """
    Recurso cuantificable de la campaña.

    Ejemplos:

        oro
        plata
        puntos de reputación
        influencia
        suministros
        comida
        munición
    """

    id: int | None = None

    name: str = ""

    resource_type: str = "generic"

    unit: str = ""

    notes: str = ""

@dataclass
class ResourceBalance:
    """
    Cantidad de un recurso que posee una entidad.
    """

    id: int | None = None

    resource_id: int = 0

    owner_id: int = 0

    amount: float = 0

    notes: str = ""