import database
from database import get_conn, init_db

from models.character_state import CharacterState
from repositories.character_repository import CharacterRepository


def create_entity(entity_id: int, name: str = "Fungoso"):
    with get_conn() as conn:
        conn.execute(
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
            """,
            (
                entity_id,
                name,
                "character",
                "Un aventurero peculiar.",
                "",
                1,
            ),
        )


def setup_database(tmp_path):
    original_db_path = database.DB_PATH
    database.DB_PATH = tmp_path / "test_campaign.db"

    init_db()

    return original_db_path


def test_character_repository_returns_none_for_missing_character(tmp_path):
    original_db_path = setup_database(tmp_path)

    try:
        repository = CharacterRepository()

        assert repository.get_character(999999) is None

    finally:
        database.DB_PATH = original_db_path


def test_character_repository_saves_and_loads_character(tmp_path):
    original_db_path = setup_database(tmp_path)

    try:
        create_entity(1)

        repository = CharacterRepository()

        character = CharacterState(
            entity_id=1,
            level=3,
            class_name="Fighter",
            current_hp=18,
            max_hp=24,
            armor_class=16,
            strength=16,
            dexterity=14,
            constitution=15,
            intelligence=10,
            wisdom=12,
            charisma=8,
            proficiency_bonus=2,
            metadata={
                "origin": "Vorder's Hold",
            },
        )

        repository.save_character(character)

        loaded = repository.get_character(1)

        assert loaded == character

    finally:
        database.DB_PATH = original_db_path


def test_character_repository_updates_existing_character(tmp_path):
    original_db_path = setup_database(tmp_path)

    try:
        create_entity(1)

        repository = CharacterRepository()

        original = CharacterState(
            entity_id=1,
            level=1,
            class_name="Fighter",
            current_hp=10,
            max_hp=10,
        )

        repository.save_character(original)

        updated = CharacterState(
            entity_id=1,
            level=2,
            class_name="Fighter",
            current_hp=15,
            max_hp=18,
            armor_class=15,
        )

        repository.save_character(updated)

        loaded = repository.get_character(1)

        assert loaded == updated

    finally:
        database.DB_PATH = original_db_path


def test_character_repository_lists_characters(tmp_path):
    original_db_path = setup_database(tmp_path)

    try:
        create_entity(1, "Fungoso")
        create_entity(2, "Aldric")

        repository = CharacterRepository()

        first = CharacterState(
            entity_id=1,
            level=1,
            class_name="Fighter",
        )

        second = CharacterState(
            entity_id=2,
            level=2,
            class_name="Rogue",
        )

        repository.save_character(first)
        repository.save_character(second)

        characters = repository.list_characters()

        assert characters == [first, second]

    finally:
        database.DB_PATH = original_db_path


def test_character_repository_deletes_character(tmp_path):
    original_db_path = setup_database(tmp_path)

    try:
        create_entity(1)

        repository = CharacterRepository()

        character = CharacterState(
            entity_id=1,
            level=1,
            class_name="Fighter",
        )

        repository.save_character(character)

        repository.delete_character(1)

        assert repository.get_character(1) is None

    finally:
        database.DB_PATH = original_db_path


def test_character_repository_delete_does_not_delete_entity(tmp_path):
    original_db_path = setup_database(tmp_path)

    try:
        create_entity(1)

        repository = CharacterRepository()

        character = CharacterState(
            entity_id=1,
            level=1,
            class_name="Fighter",
        )

        repository.save_character(character)
        repository.delete_character(1)

        assert repository.get_character(1) is None

        with database.get_conn() as conn:
            row = conn.execute(
                """
                SELECT id
                FROM entities
                WHERE id=?
                """,
                (1,),
            ).fetchone()

        assert row is not None
        assert row["id"] == 1

    finally:
        database.DB_PATH = original_db_path