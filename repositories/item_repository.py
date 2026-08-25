from database import rows, one, execute


class ItemRepository:

    # =========================================================
    # ITEMS
    # =========================================================

    def get_all(self):
        return rows(
            """
            SELECT *
            FROM items
            ORDER BY id
            """
        )

    def get_by_id(
        self,
        item_id: int,
    ):
        return one(
            """
            SELECT *
            FROM items
            WHERE id=?
            """,
            (item_id,),
        )

    def get_by_name(
        self,
        name: str,
    ):
        if not name:
            return None

        return one(
            """
            SELECT *
            FROM items
            WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
            LIMIT 1
            """,
            (name,),
        )

    def search(
        self,
        query: str,
    ):
        if not query:
            return self.get_all()

        like = f"%{query}%"

        return rows(
            """
            SELECT *
            FROM items
            WHERE name LIKE ?
               OR description LIKE ?
               OR significance LIKE ?
               OR notes LIKE ?
            ORDER BY id
            """,
            (
                like,
                like,
                like,
                like,
            ),
        )

    # =========================================================
    # CREATE
    # =========================================================

    def create(
        self,
        data: dict,
    ) -> int:

        return execute(
            """
            INSERT INTO items
                (
                    name,
                    description,
                    significance,
                    unique_item,
                    notes
                )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data.get("description", ""),
                data.get("significance", ""),
                int(bool(data.get("unique", False))),
                data.get("notes", ""),
            ),
        )

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        item_id: int,
        data: dict,
    ) -> None:

        execute(
            """
            UPDATE items
            SET
                name=?,
                description=?,
                significance=?,
                unique_item=?,
                notes=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data["name"],
                data.get("description", ""),
                data.get("significance", ""),
                int(bool(data.get("unique", False))),
                data.get("notes", ""),
                item_id,
            ),
        )

    # =========================================================
    # INSTANCES
    # =========================================================

    def get_instances(
        self,
        item_id: int,
    ):
        return rows(
            """
            SELECT *
            FROM item_instances
            WHERE item_id=?
            ORDER BY instance_number
            """,
            (item_id,),
        )

    def get_instance_by_id(
        self,
        instance_id: int,
    ):
        return one(
            """
            SELECT *
            FROM item_instances
            WHERE id=?
            """,
            (instance_id,),
        )

    def get_instances_by_owner(
        self,
        item_id: int,
        owner_id: int,
    ):
        return rows(
            """
            SELECT *
            FROM item_instances
            WHERE item_id=?
              AND owner_id=?
              AND active=1
            ORDER BY instance_number
            """,
            (
                item_id,
                owner_id,
            ),
        )

    def create_instance(
        self,
        data: dict,
    ) -> int:

        return execute(
            """
            INSERT INTO item_instances
                (
                    item_id,
                    instance_number,
                    owner_id,
                    location_id,
                    condition,
                    notes,
                    active
                )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["item_id"],
                data.get("instance_number", 1),
                data.get("owner_id"),
                data.get("location_id"),
                data.get("condition", ""),
                data.get("notes", ""),
                int(bool(data.get("active", True))),
            ),
        )

    def update_instance(
        self,
        instance_id: int,
        data: dict,
    ) -> None:

        execute(
            """
            UPDATE item_instances
            SET
                item_id=?,
                instance_number=?,
                owner_id=?,
                location_id=?,
                condition=?,
                notes=?,
                active=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data["item_id"],
                data.get("instance_number", 1),
                data.get("owner_id"),
                data.get("location_id"),
                data.get("condition", ""),
                data.get("notes", ""),
                int(bool(data.get("active", True))),
                instance_id,
            ),
        )