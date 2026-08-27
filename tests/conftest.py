import pytest


@pytest.fixture(autouse=True)
def isolated_database(tmp_path, monkeypatch):
    """
    Aísla cada test en una base SQLite temporal.
    """

    import database

    test_db_path = tmp_path / "campaign_test.db"

    monkeypatch.setattr(
        database,
        "DB_PATH",
        test_db_path,
    )

    database.init_db()

    import app
    from services.world_service import WorldService

    test_world_service = WorldService()
    test_world_service.load()

    monkeypatch.setattr(
        app,
        "world_service",
        test_world_service,
    )

    yield