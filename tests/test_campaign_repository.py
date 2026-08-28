from repositories.campaign_repository import CampaignRepository


def test_get_campaign_returns_none_for_missing_campaign():
    repository = CampaignRepository()

    assert repository.get_campaign(999999) is None


def test_get_session_returns_none_for_missing_session():
    repository = CampaignRepository()

    assert repository.get_session(999999) is None


def test_get_current_session_returns_none_for_missing_campaign():
    repository = CampaignRepository()

    assert repository.get_current_session(999999) is None


def test_create_session_and_get_session():
    repository = CampaignRepository()

    session = repository.create_session(
        number=999,
        title="Test Session",
        summary="Resumen de prueba.",
        start_location="Vorder's Hold",
        end_location="La mina",
        notes="Notas de prueba.",
    )

    assert session is not None
    assert session["number"] == 999
    assert session["title"] == "Test Session"
    assert session["summary"] == "Resumen de prueba."
    assert session["start_location"] == "Vorder's Hold"
    assert session["end_location"] == "La mina"
    assert session["notes"] == "Notas de prueba."


def test_get_current_session_returns_none_when_campaign_has_no_session(
    isolated_database,
):
    repository = CampaignRepository()

    # Crear explícitamente la campaña necesaria para este test.
    from database import execute

    execute(
        """
        INSERT INTO campaign (
            id,
            name,
            system,
            tone,
            summary
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            1,
            "Test Campaign",
            "D&D 5e 2014",
            "",
            "",
        ),
    )

    campaign = repository.get_campaign(1)

    assert campaign is not None
    assert campaign["current_session_id"] is None

    assert repository.get_current_session(1) is None


def test_update_current_session_and_get_current_session(
    isolated_database,
):
    repository = CampaignRepository()

    from database import execute

    execute(
        """
        INSERT INTO campaign (
            id,
            name,
            system,
            tone,
            summary
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            1,
            "Test Campaign",
            "D&D 5e 2014",
            "",
            "",
        ),
    )

    session = repository.create_session(
        number=998,
        title="Current Session",
        summary="Sesión actual.",
        start_location="Vorder's Hold",
        end_location="La mina",
        notes="",
    )

    session_id = session["id"]

    repository.update_current_session(
        campaign_id=1,
        session_id=session_id,
    )

    current_session = repository.get_current_session(1)

    assert current_session is not None
    assert current_session["id"] == session_id
    assert current_session["title"] == "Current Session"