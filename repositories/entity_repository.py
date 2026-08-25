from database import rows, one, execute


class EntityRepository:

    # =========================================================
    # READ
    # =========================================================

    def get_all(self):
        return rows(
            """
            SELECT *
            FROM entities
            ORDER BY id
            """
        )

    def get_by_id(
        self,
        entity_id: int,
    ):
        return one(
            """
            SELECT *
            FROM entities
            WHERE id=?
            """,
            (entity_id,),
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
            FROM entities
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
            FROM entities
            WHERE name LIKE ?
               OR entity_type LIKE ?
               OR description LIKE ?
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

    def get_by_type(
        self,
        entity_type: str,
    ):
        return rows(
            """
            SELECT *
            FROM entities
            WHERE entity_type=?
            ORDER BY id
            """,
            (entity_type,),
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
            INSERT INTO entities
                (
                    name,
                    entity_type,
                    description,
                    notes,
                    active
                )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                data["name"],
                data.get("entity_type", ""),
                data.get("description", ""),
                data.get("notes", ""),
                int(bool(data.get("active", True))),
            ),
        )

    # =========================================================
    # UPDATE
    # =========================================================

    def update(
        self,
        entity_id: int,
        data: dict,
    ) -> None:

        execute(
            """
            UPDATE entities
            SET
                name=?,
                entity_type=?,
                description=?,
                notes=?,
                active=?,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data["name"],
                data.get("entity_type", ""),
                data.get("description", ""),
                data.get("notes", ""),
                int(bool(data.get("active", True))),
                entity_id,
            ),
        )

    # =========================================================
    # ACTIVATE / DEACTIVATE
    # =========================================================

    def deactivate(
        self,
        entity_id: int,
    ) -> None:

        execute(
            """
            UPDATE entities
            SET
                active=0,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (entity_id,),
        )

    def activate(
        self,
        entity_id: int,
    ) -> None:

        execute(
            """
            UPDATE entities
            SET
                active=1,
                updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (entity_id,),
        )