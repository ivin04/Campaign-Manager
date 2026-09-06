from dataclasses import dataclass


@dataclass
class Entity:
    """
    Entidad persistente de la campaña.

    Representa algo que existe dentro del mundo:
    personaje, objeto, lugar, facción, criatura, etc.
    """

    id: int | None = None

    name: str = ""

    entity_type: str = ""

    description: str = ""

    notes: str = ""

    active: bool = True