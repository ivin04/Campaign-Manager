from database import (
    get_conn,
    execute_in_conn,
    one_in_conn,
)


def test_execute_in_conn_and_one_in_conn_share_transaction():
    with get_conn() as conn:

        execute_in_conn(
            conn,
            """
            CREATE TEMP TABLE test_transaction (
                id INTEGER PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
        )

        execute_in_conn(
            conn,
            """
            INSERT INTO test_transaction (
                id,
                value
            )
            VALUES (?, ?)
            """,
            (1, "ok"),
        )

        row = one_in_conn(
            conn,
            """
            SELECT
                id,
                value
            FROM test_transaction
            WHERE id=?
            """,
            (1,),
        )

        assert row == {
            "id": 1,
            "value": "ok",
        }