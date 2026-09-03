from __future__ import annotations

from models.turn_record import TurnRecord

from database import (
    execute,
    execute_in_conn,
    one,
    one_in_conn,
    rows,
    get_conn,
)


class TurnRepository:
    """
    Persistencia de los turnos de campaña.

    Este repository no conoce el LLM ni el WorldState.
    """

    @staticmethod
    def _validate_positive_int(
        value,
        field_name: str,
    ) -> None:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
        ):
            raise TypeError(
                f"{field_name} must be an integer"
            )

        if value < 1:
            raise ValueError(
                f"{field_name} must be greater than zero"
            )

    @staticmethod
    def _validate_optional_positive_int(
        value,
        field_name: str,
    ) -> None:
        if value is None:
            return

        TurnRepository._validate_positive_int(
            value,
            field_name,
        )

    @staticmethod
    def _validate_external_turn_id(
        value: str,
    ) -> str:
        if not isinstance(
            value,
            str,
        ):
            raise TypeError(
                "external_turn_id must be a string"
            )

        value = value.strip()

        if not value:
            raise ValueError(
                "external_turn_id must not be empty"
            )

        if len(value) > 500:
            raise ValueError(
                "external_turn_id must not be longer than 500 characters"
            )

        return value

    def save_turn(
        self,
        turn: TurnRecord,
        *,
        conn=None,
    ) -> TurnRecord:

        if not isinstance(
            turn,
            TurnRecord,
        ):
            raise TypeError(
                "turn must be a TurnRecord"
            )

        if not isinstance(
            turn.player_input,
            str,
        ):
            raise TypeError(
                "turn.player_input must be a string"
            )

        if not isinstance(
            turn.narrative,
            str,
        ):
            raise TypeError(
                "turn.narrative must be a string"
            )

        external_turn_id = None

        if turn.external_turn_id is not None:
            external_turn_id = (
                self._validate_external_turn_id(
                    turn.external_turn_id
                )
            )

        query = """
            INSERT INTO turns (
                session_id,
                player_input,
                narrative,
                operation_count,
                successful_operation_count,
                failed_operation_count,
                all_operations_succeeded,
                world_changed,
                external_turn_id,
                version,
                status,
                snapshot
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        params = (
            turn.session_id,
            turn.player_input,
            turn.narrative,
            turn.operation_count,
            turn.successful_operation_count,
            turn.failed_operation_count,
            int(turn.all_operations_succeeded),
            int(turn.world_changed),
            external_turn_id,
            turn.version,
            turn.status,
            turn.snapshot,
        )

        if conn is None:
            turn_id = execute(
                query,
                params,
            )

            row = one(
                """
                SELECT
                    id,
                    session_id,
                    player_input,
                    narrative,
                    operation_count,
                    successful_operation_count,
                    failed_operation_count,
                    all_operations_succeeded,
                    world_changed,
                    created_at,
                    external_turn_id
                FROM turns
                WHERE id=?
                """,
                (turn_id,),
            )

        else:
            turn_id = execute_in_conn(
                conn,
                query,
                params,
            )

            row = one_in_conn(
                conn,
                """
                SELECT
                    id,
                    session_id,
                    player_input,
                    narrative,
                    operation_count,
                    successful_operation_count,
                    failed_operation_count,
                    all_operations_succeeded,
                    world_changed,
                    created_at,
                    external_turn_id
                FROM turns
                WHERE id=?
                """,
                (turn_id,),
            )

        if row is None:
            raise RuntimeError(
                "failed to retrieve saved turn"
            )

        return self._row_to_model(row)

    def get_turn(
        self,
        turn_id: int,
    ) -> TurnRecord | None:

        self._validate_positive_int(
            turn_id,
            "turn_id",
        )

        row = one(
            """
            SELECT
                id,
                session_id,
                player_input,
                narrative,
                operation_count,
                successful_operation_count,
                failed_operation_count,
                all_operations_succeeded,
                world_changed,
                created_at,
                external_turn_id
            FROM turns
            WHERE id=?
            """,
            (turn_id,),
        )

        if row is None:
            return None

        return self._row_to_model(row)

    def get_by_external_turn_id(
        self,
        external_turn_id: str,
        *,
        conn=None,
    ) -> TurnRecord | None:

        normalized_id = (
            self._validate_external_turn_id(
                external_turn_id
            )
        )

        query = """
            SELECT
                id,
                session_id,
                player_input,
                narrative,
                operation_count,
                successful_operation_count,
                failed_operation_count,
                all_operations_succeeded,
                world_changed,
                created_at,
                external_turn_id
            FROM turns
            WHERE external_turn_id=?
        """

        if conn is None:
            row = one(
                query,
                (normalized_id,),
            )
        else:
            row = one_in_conn(
                conn,
                query,
                (normalized_id,),
            )

        if row is None:
            return None

        return self._row_to_model(row)

    def list_turns(
        self,
        *,
        session_id: int | None = None,
        limit: int | None = None,
    ) -> list[TurnRecord]:

        self._validate_optional_positive_int(
            session_id,
            "session_id",
        )

        if limit is not None:
            if not isinstance(
                limit,
                int,
            ):
                raise TypeError(
                    "limit must be an integer"
                )

            if limit < 1:
                raise ValueError(
                    "limit must be greater than zero"
                )

            if limit > 100:
                raise ValueError(
                    "limit must not be greater than 100"
                )

        if session_id is None:
            if limit is None:
                result = rows(
                    """
                    SELECT
                        id,
                        session_id,
                        player_input,
                        narrative,
                        operation_count,
                        successful_operation_count,
                        failed_operation_count,
                        all_operations_succeeded,
                        world_changed,
                        created_at,
                        external_turn_id
                    FROM turns
                    ORDER BY id ASC
                    """
                )
            else:
                result = rows(
                    """
                    SELECT
                        id,
                        session_id,
                        player_input,
                        narrative,
                        operation_count,
                        successful_operation_count,
                        failed_operation_count,
                        all_operations_succeeded,
                        world_changed,
                        created_at,
                        external_turn_id
                    FROM turns
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (limit,),
                )

        else:
            if limit is None:
                result = rows(
                    """
                    SELECT
                        id,
                        session_id,
                        player_input,
                        narrative,
                        operation_count,
                        successful_operation_count,
                        failed_operation_count,
                        all_operations_succeeded,
                        world_changed,
                        created_at,
                        external_turn_id
                    FROM turns
                    WHERE session_id=?
                    ORDER BY id ASC
                    """,
                    (session_id,),
                )
            else:
                result = rows(
                    """
                    SELECT
                        id,
                        session_id,
                        player_input,
                        narrative,
                        operation_count,
                        successful_operation_count,
                        failed_operation_count,
                        all_operations_succeeded,
                        world_changed,
                        created_at,
                        external_turn_id
                    FROM turns
                    WHERE session_id=?
                    ORDER BY id ASC
                    LIMIT ?
                    """,
                    (
                        session_id,
                        limit,
                    ),
                )

        return [
            self._row_to_model(row)
            for row in result
        ]

    def list_recent_turns(
        self,
        *,
        session_id: int | None = None,
        limit: int = 10,
    ) -> list[TurnRecord]:

        self._validate_optional_positive_int(
            session_id,
            "session_id",
        )

        if not isinstance(
            limit,
            int,
        ):
            raise TypeError(
                "limit must be an integer"
            )

        if limit < 1:
            raise ValueError(
                "limit must be greater than zero"
            )

        if limit > 100:
            raise ValueError(
                "limit must not be greater than 100"
            )

        if session_id is None:
            result = rows(
                """
                SELECT
                    id,
                    session_id,
                    player_input,
                    narrative,
                    operation_count,
                    successful_operation_count,
                    failed_operation_count,
                    all_operations_succeeded,
                    world_changed,
                    created_at,
                    external_turn_id
                FROM turns
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            )

        else:
            result = rows(
                """
                SELECT
                    id,
                    session_id,
                    player_input,
                    narrative,
                    operation_count,
                    successful_operation_count,
                    failed_operation_count,
                    all_operations_succeeded,
                    world_changed,
                    created_at,
                    external_turn_id
                FROM turns
                WHERE session_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (
                    session_id,
                    limit,
                ),
            )

        return [
            self._row_to_model(row)
            for row in reversed(result)
        ]

    @staticmethod
    def _row_to_model(
        row: dict,
    ) -> TurnRecord:

        return TurnRecord(
            id=row["id"],
            session_id=row["session_id"],
            player_input=row["player_input"],
            narrative=row["narrative"],
            operation_count=row["operation_count"],
            successful_operation_count=(
                row["successful_operation_count"]
            ),
            failed_operation_count=(
                row["failed_operation_count"]
            ),
            all_operations_succeeded=bool(
                row["all_operations_succeeded"]
            ),
            world_changed=bool(
                row["world_changed"]
            ),
            created_at=row["created_at"],
            external_turn_id=row["external_turn_id"],
        )

    def get_active_by_external_turn_id(
        self,
        external_turn_id: str,
        *,
        conn=None,
    ) -> TurnRecord | None:

        if conn is None:
            with get_conn() as connection:
                return self.get_active_by_external_turn_id(
                    external_turn_id,
                    conn=connection,
                )

        row = conn.execute(
            """
            SELECT
                id,
                session_id,
                player_input,
                narrative,
                operation_count,
                successful_operation_count,
                failed_operation_count,
                all_operations_succeeded,
                world_changed,
                created_at,
                external_turn_id,
                version,
                status,
                snapshot
            FROM turns
            WHERE external_turn_id=?
            AND status='active'
            ORDER BY version DESC
            LIMIT 1
            """,
            (external_turn_id,),
        ).fetchone()

        if row is None:
            return None

        return self._row_to_turn_record(row)

    def get_versions_by_external_turn_id(
        self,
        external_turn_id: str,
        *,
        conn=None,
    ) -> list[TurnRecord]:

        if conn is None:
            with get_conn() as connection:
                return self.get_versions_by_external_turn_id(
                    external_turn_id,
                    conn=connection,
                )

        rows = conn.execute(
            """
            SELECT
                id,
                session_id,
                player_input,
                narrative,
                operation_count,
                successful_operation_count,
                failed_operation_count,
                all_operations_succeeded,
                world_changed,
                created_at,
                external_turn_id,
                version,
                status,
                snapshot
            FROM turns
            WHERE external_turn_id=?
            ORDER BY version ASC
            """,
            (external_turn_id,),
        ).fetchall()

        return [
            self._row_to_turn_record(row)
            for row in rows
        ]

    def supersede_turn(
        self,
        turn_id: int,
        *,
        conn,
    ) -> None:

        conn.execute(
            """
            UPDATE turns
            SET status='superseded'
            WHERE id=?
            """,
            (turn_id,),
        )