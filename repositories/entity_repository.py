from __future__ import annotations

from database import (
    execute,
    one,
    rows,
    one_in_conn,
)
from models.entity import Entity


class EntityRepository:
    """Repositorio de entidades persistentes."""

    def get_entity(
        self,
        entity_id: int,
        *,
        conn=None,
    ) -> Entity | None:

        query = """
            SELECT
                id,
                name,
                entity_type,
                description,
                notes,
                active
            FROM entities
            WHERE id=?
        """

        if conn is None:
            row = one(
                query,
                (entity_id,),
            )
        else:
            row = one_in_conn(
                conn,
                query,
                (entity_id,),
            )

        if row is None:
            return None

        return self._row_to_model(row)

    def save_entity(
        self,
        entity: Entity,
    ) -> Entity:

        if entity.id is None:
            entity_id = execute(
                """
                INSERT INTO entities (
                    name,
                    entity_type,
                    description,
                    notes,
                    active
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    entity.name,
                    entity.entity_type,
                    entity.description,
                    entity.notes,
                    int(entity.active),
                ),
            )

        else:
            execute(
                """
                INSERT INTO entities (
                    id,
                    name,
                    entity_type,
                    description,
                    notes,
                    active
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id)
                DO UPDATE SET
                    name=excluded.name,
                    entity_type=excluded.entity_type,
                    description=excluded.description,
                    notes=excluded.notes,
                    active=excluded.active,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (
                    entity.id,
                    entity.name,
                    entity.entity_type,
                    entity.description,
                    entity.notes,
                    int(entity.active),
                ),
            )

            entity_id = entity.id

        loaded = self.get_entity(entity_id)

        if loaded is None:
            raise RuntimeError(
                f"Entity {entity_id} could not be loaded after save"
            )

        return loaded

    def delete_entity(
        self,
        entity_id: int,
    ) -> None:

        execute(
            """
            DELETE FROM entities
            WHERE id=?
            """,
            (entity_id,),
        )

    def list_entities(self) -> list[Entity]:

        rows_data = rows(
            """
            SELECT
                id,
                name,
                entity_type,
                description,
                notes,
                active
            FROM entities
            ORDER BY id
            """
        )

        return [
            self._row_to_model(row)
            for row in rows_data
        ]

    @staticmethod
    def _row_to_model(row) -> Entity:

        return Entity(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            description=row["description"],
            notes=row["notes"],
            active=bool(row["active"]),
        )