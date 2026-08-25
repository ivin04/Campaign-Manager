from database import rows, one, execute


def get_all():
    return rows(
        "SELECT * FROM items ORDER BY id"
    )


def search(query: str):
    like = f"%{query}%"

    return rows(
        """
        SELECT *
        FROM items
        WHERE name LIKE ?
           OR description LIKE ?
           OR owner LIKE ?
           OR location LIKE ?
           OR notes LIKE ?
        """,
        (
            like,
            like,
            like,
            like,
            like,
        )
    )


def get_by_id(item_id: int):
    return one(
        "SELECT * FROM items WHERE id=?",
        (item_id,)
    )


def get_by_name(name: str):
    return one(
        """
        SELECT *
        FROM items
        WHERE LOWER(name) = LOWER(?)
        LIMIT 1
        """,
        (name.strip(),)
    )


def create(data: dict):
    return execute(
        """
        INSERT INTO items
            (name, description, owner, location, significance, notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data["name"],
            data["description"],
            data["owner"],
            data["location"],
            data["significance"],
            data["notes"],
        )
    )


def update(item_id: int, data: dict):
    execute(
        """
        UPDATE items
        SET description=?,
            owner=?,
            location=?,
            significance=?,
            notes=?,
            updated_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (
            data["description"],
            data["owner"],
            data["location"],
            data["significance"],
            data["notes"],
            item_id,
        )
    )