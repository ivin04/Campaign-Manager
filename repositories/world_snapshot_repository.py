import json


class WorldSnapshotRepository:
    """
    Persiste snapshots completos del estado mutable de la campaña.

    El snapshot está diseñado para permitir reconciliación de turnos:
    
        snapshot
            ↓
        restaurar estado anterior
            ↓
        aplicar nueva versión

    No contiene la tabla turns.
    """

    SNAPSHOT_TABLES = (
        "entities",
        "items",
        "item_instances",
        "resources",
        "resource_balances",
        "relations",
        "world_events",
        "character_states",
    )

    RESTORE_DELETE_ORDER = (
        "world_events",
        "relations",
        "resource_balances",
        "item_instances",
        "character_states",
        "resources",
        "items",
        "entities",
    )

    RESTORE_INSERT_ORDER = (
        "entities",
        "items",
        "item_instances",
        "resources",
        "resource_balances",
        "relations",
        "world_events",
        "character_states",
    )

    def create_snapshot(self, conn) -> str:
        """
        Crea un snapshot JSON del estado actual.

        Debe llamarse dentro de la misma transacción que
        posteriormente aplicará el turno.
        """

        snapshot = {}

        for table in self.SNAPSHOT_TABLES:
            rows = conn.execute(
                f"SELECT * FROM {table}"
            ).fetchall()

            snapshot[table] = [
                dict(row)
                for row in rows
            ]

        return json.dumps(
            snapshot,
            ensure_ascii=False,
            separators=(",", ":"),
        )

    def restore_snapshot(
        self,
        conn,
        snapshot: str,
    ) -> None:
        """
        Restaura exactamente el estado contenido en el snapshot.

        Se utiliza para revertir una versión anterior de un turno
        antes de aplicar una nueva versión.
        """

        if not isinstance(snapshot, str):
            raise TypeError(
                "snapshot must be a string"
            )

        try:
            data = json.loads(snapshot)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Invalid world snapshot JSON"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "World snapshot must contain an object"
            )

        missing_tables = [
            table
            for table in self.SNAPSHOT_TABLES
            if table not in data
        ]

        if missing_tables:
            raise ValueError(
                "World snapshot is missing tables: "
                + ", ".join(missing_tables)
            )

        # ------------------------------------------------------------
        # DELETE CURRENT STATE
        # ------------------------------------------------------------

        for table in self.RESTORE_DELETE_ORDER:
            conn.execute(
                f"DELETE FROM {table}"
            )

        # ------------------------------------------------------------
        # RESTORE SNAPSHOT
        # ------------------------------------------------------------

        for table in self.RESTORE_INSERT_ORDER:
            table_rows = data[table]

            if not isinstance(table_rows, list):
                raise ValueError(
                    f"Snapshot table '{table}' must contain a list"
                )

            for row in table_rows:

                if not isinstance(row, dict):
                    raise ValueError(
                        f"Snapshot row in '{table}' "
                        "must contain an object"
                    )

                if not row:
                    continue

                columns = list(row.keys())

                placeholders = ",".join(
                    "?" for _ in columns
                )

                column_sql = ",".join(
                    f'"{column}"'
                    for column in columns
                )

                conn.execute(
                    f"""
                    INSERT INTO "{table}" (
                        {column_sql}
                    )
                    VALUES (
                        {placeholders}
                    )
                    """,
                    [
                        row[column]
                        for column in columns
                    ],
                )