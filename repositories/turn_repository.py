from __future__ import annotations

from models.turn_record import TurnRecord
from database import (
    execute,
    execute_in_conn,
    one,
    one_in_conn,
    rows,
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

    def save_turn(
        self,
        turn: TurnRecord,
        *,
        conn=None,
    ) -> TurnRecord:

        if not isinstance(turn, TurnRecord):
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

        query = """
            INSERT INTO turns (
                session_id,
                player_input,
                narrative,
                operation_count,
                successful_operation_count,
                failed_operation_count,
                all_operations_succeeded,
                world_changed
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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
                    created_at
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
                    created_at
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
                created_at
            FROM turns
            WHERE id=?
            """,
            (turn_id,),
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
            if not isinstance(limit, int):
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
                        created_at
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
                        created_at
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
                        created_at
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
                        created_at
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
        """
        Devuelve los últimos turnos guardados.

        Los resultados se devuelven en orden cronológico ascendente,
        del más antiguo al más reciente.
        """

        self._validate_optional_positive_int(
            session_id,
            "session_id",
        )

        if not isinstance(limit, int):
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
                    created_at
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
                    created_at
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
    def _row_to_model(row: dict) -> TurnRecord:
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
        )