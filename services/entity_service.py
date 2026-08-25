from repositories.entity_repository import EntityRepository


class EntityService:

    def __init__(
        self,
        repository: EntityRepository | None = None,
    ):
        self.repository = repository or EntityRepository()

    # =========================================================
    # READ
    # =========================================================

    def get_all(self):
        return self.repository.get_all()

    def get_by_id(self, entity_id: int):
        return self.repository.get_by_id(entity_id)

    def get_by_name(self, name: str):
        if not name:
            return None

        return self.repository.get_by_name(name)

    def search(self, query: str):
        return self.repository.search(query)

    def get_by_type(self, entity_type: str):
        return self.repository.get_by_type(entity_type)

    # =========================================================
    # CREATE
    # =========================================================

    def create(self, data: dict) -> int:

        name = str(data.get("name") or "").strip()

        if not name:
            raise ValueError("Entity name is required")

        existing = self.repository.get_by_name(name)

        if existing:
            raise ValueError(
                f"Entity already exists: {existing['name']}"
            )

        payload = {
            "name": name,
            "entity_type": data.get("entity_type", ""),
            "description": data.get("description", ""),
            "notes": data.get("notes", ""),
            "active": data.get("active", True),
        }

        return self.repository.create(payload)

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        entity_id: int,
        data: dict,
    ) -> None:

        existing = self.repository.get_by_id(entity_id)

        if not existing:
            raise ValueError(
                f"Entity not found: {entity_id}"
            )

        name = str(
            data.get("name", existing["name"])
            or ""
        ).strip()

        if not name:
            raise ValueError("Entity name is required")

        other = self.repository.get_by_name(name)

        if other and other["id"] != entity_id:
            raise ValueError(
                f"Entity already exists: {other['name']}"
            )

        payload = {
            "name": name,
            "entity_type": data.get(
                "entity_type",
                existing.get("entity_type", ""),
            ),
            "description": data.get(
                "description",
                existing.get("description", ""),
            ),
            "notes": data.get(
                "notes",
                existing.get("notes", ""),
            ),
            "active": data.get(
                "active",
                existing.get("active", True),
            ),
        }

        self.repository.update(
            entity_id,
            payload,
        )

    # =========================================================
    # STATE
    # =========================================================

    def deactivate(
        self,
        entity_id: int,
    ) -> None:

        existing = self.repository.get_by_id(entity_id)

        if not existing:
            raise ValueError(
                f"Entity not found: {entity_id}"
            )

        self.repository.deactivate(entity_id)

    def activate(
        self,
        entity_id: int,
    ) -> None:

        existing = self.repository.get_by_id(entity_id)

        if not existing:
            raise ValueError(
                f"Entity not found: {entity_id}"
            )

        self.repository.activate(entity_id)