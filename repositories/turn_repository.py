from __future__ import annotations

from models.turn_record import TurnRecord
from database import execute, one, rows


class TurnRepository:
    """
    Persistencia de los turnos de campaña.

    Este repository no conoce el LLM ni el WorldState.
    """

    def save_turn(
        self,
        turn: TurnRecord,
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

        turn_id = execute(
            """
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
            """,
            (
                turn.session_id,
                turn.player_input,
                turn.narrative,
                turn.operation_count,
                turn.successful_operation_count,
                turn.failed_operation_count,
                int(turn.all_operations_succeeded),
                int(turn.world_changed),
            ),
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
            raise RuntimeError(
                "failed to retrieve saved turn"
            )

        return self._row_to_model(row)

    def get_turn(
        self,
        turn_id: int,
    ) -> TurnRecord | None:

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
    ) -> list[TurnRecord]:

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
                WHERE session_id=?
                ORDER BY id ASC
                """,
                (session_id,),
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