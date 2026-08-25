from models.entity import Entity


class EntityResolver:

    def __init__(self, entities: dict[int, Entity]):
        self.entities = entities

    def find(
        self,
        name: str,
    ) -> Entity | None:

        if not name:
            return None

        normalized = name.strip().casefold()

        for entity in self.entities.values():

            if entity.name.strip().casefold() == normalized:
                return entity

        return None