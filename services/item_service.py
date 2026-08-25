from repositories.item_repository import ItemRepository

from services.identity_service import names_match


ITEM_SYNONYM_GROUPS = [
    ["anillo", "aro", "sortija"],
]


class ItemService:

    def __init__(
        self,
        repository: ItemRepository | None = None,
    ):
        self.repository = repository or ItemRepository()

    # =========================================================
    # READ
    # =========================================================

    def get_all(self):
        return self.repository.get_all()

    def get_by_id(
        self,
        item_id: int,
    ):
        return self.repository.get_by_id(item_id)

    def get_by_name(
        self,
        name: str,
    ):
        return self.repository.get_by_name(name)

    def search(
        self,
        query: str,
    ):
        return self.repository.search(query)

    # =========================================================
    # IDENTITY
    # =========================================================

    def find_matching_item(
        self,
        name: str,
    ):
        if not name:
            return None

        existing_items = self.repository.get_all()

        for existing in existing_items:

            existing_name = existing.get("name")

            if not existing_name:
                continue

            if names_match(
                name,
                existing_name,
                ITEM_SYNONYM_GROUPS,
            ):
                return existing

        return None

    # =========================================================
    # CREATE
    # =========================================================

    def create(
        self,
        data: dict,
    ):

        name = str(
            data.get("name") or ""
        ).strip()

        if not name:
            raise ValueError(
                "Item name is required"
            )

        existing = self.find_matching_item(name)

        if existing:
            raise ValueError(
                f"Item already exists: {existing['name']}"
            )

        payload = {
            "name": name,
            "description": data.get(
                "description",
                "",
            ),
            "significance": data.get(
                "significance",
                "",
            ),
            "unique": data.get(
                "unique",
                False,
            ),
            "notes": data.get(
                "notes",
                "",
            ),
        }

        item_id = self.repository.create(
            payload
        )

        return self.repository.get_by_id(
            item_id
        )

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        item_id: int,
        data: dict,
    ) -> None:

        existing = self.repository.get_by_id(
            item_id
        )

        if not existing:
            raise ValueError(
                f"Item not found: {item_id}"
            )

        name = str(
            data.get(
                "name",
                existing["name"],
            )
            or ""
        ).strip()

        if not name:
            raise ValueError(
                "Item name is required"
            )

        matching = self.find_matching_item(
            name
        )

        if matching and matching["id"] != item_id:
            raise ValueError(
                f"Item already exists: {matching['name']}"
            )

        payload = {
            "name": name,
            "description": data.get(
                "description",
                existing.get("description", ""),
            ),
            "significance": data.get(
                "significance",
                existing.get("significance", ""),
            ),
            "unique": data.get(
                "unique",
                bool(existing.get("unique_item", 0)),
            ),
            "notes": data.get(
                "notes",
                existing.get("notes", ""),
            ),
        }

        self.repository.update(
            item_id,
            payload,
        )

    # =========================================================
    # INSTANCES
    # =========================================================

    def get_instances(
        self,
        item_id: int,
    ):
        return self.repository.get_instances(
            item_id
        )

    def get_instance(
        self,
        instance_id: int,
    ):
        return self.repository.get_instance_by_id(
            instance_id
        )

    def get_instances_by_owner(
        self,
        item_id: int,
        owner_id: int,
    ):
        return self.repository.get_instances_by_owner(
            item_id,
            owner_id,
        )

    def create_instance(
        self,
        data: dict,
    ):

        item = self.repository.get_by_id(
            data["item_id"]
        )

        if not item:
            raise ValueError(
                f"Item not found: {data['item_id']}"
            )

        instance_id = self.repository.create_instance(
            data
        )

        return self.repository.get_instance_by_id(
            instance_id
        )

    def update_instance(
        self,
        instance_id: int,
        data: dict,
    ) -> None:

        existing = self.repository.get_instance_by_id(
            instance_id
        )

        if not existing:
            raise ValueError(
                f"Item instance not found: {instance_id}"
            )

        self.repository.update_instance(
            instance_id,
            data,
        )