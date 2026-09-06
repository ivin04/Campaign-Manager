import pytest

from models.schemas import (
    SillyTavernContextIn,
    SillyTavernTurnIn,
)


# ============================================================
# SCHEMAS
# ============================================================


def test_silly_tavern_context_schema_accepts_query():
    data = SillyTavernContextIn(
        query="Entro en la taberna."
    )

    assert data.query == (
        "Entro en la taberna."
    )


def test_silly_tavern_context_schema_strips_query():
    data = SillyTavernContextIn(
        query="  Entro en la taberna.  "
    )

    assert data.query == (
        "Entro en la taberna."
    )


def test_silly_tavern_context_schema_rejects_empty_query():
    with pytest.raises(ValueError):
        SillyTavernContextIn(
            query="   "
        )


def test_silly_tavern_turn_schema_accepts_valid_data():
    data = SillyTavernTurnIn(
        player_input="Abro la puerta.",
        narrative=(
            "La puerta se abre con un chirrido "
            "lento y desagradable."
        ),
    )

    assert data.player_input == (
        "Abro la puerta."
    )

    assert data.narrative == (
        "La puerta se abre con un chirrido "
        "lento y desagradable."
    )


def test_silly_tavern_turn_schema_strips_text():
    data = SillyTavernTurnIn(
        player_input="  Abro la puerta.  ",
        narrative="  La puerta se abre.  ",
    )

    assert data.player_input == (
        "Abro la puerta."
    )

    assert data.narrative == (
        "La puerta se abre."
    )


def test_silly_tavern_turn_schema_rejects_empty_player_input():
    with pytest.raises(ValueError):
        SillyTavernTurnIn(
            player_input="   ",
            narrative="Narrativa.",
        )


def test_silly_tavern_turn_schema_rejects_empty_narrative():
    with pytest.raises(ValueError):
        SillyTavernTurnIn(
            player_input="Abro la puerta.",
            narrative="   ",
        )


# ============================================================
# API
# ============================================================


def test_integration_context_endpoint_rejects_missing_query(
    client,
):
    response = client.post(
        "/integration/context",
        json={},
    )

    assert response.status_code == 422


def test_integration_context_endpoint_rejects_empty_query(
    client,
):
    response = client.post(
        "/integration/context",
        json={
            "query": "",
        },
    )

    assert response.status_code == 422


def test_integration_turn_endpoint_rejects_missing_fields(
    client,
):
    response = client.post(
        "/integration/turn",
        json={},
    )

    assert response.status_code == 422


def test_integration_turn_endpoint_rejects_empty_player_input(
    client,
):
    response = client.post(
        "/integration/turn",
        json={
            "player_input": "",
            "narrative": "Narrativa.",
        },
    )

    assert response.status_code == 422


def test_integration_turn_endpoint_rejects_empty_narrative(
    client,
):
    response = client.post(
        "/integration/turn",
        json={
            "player_input": "Abro la puerta.",
            "narrative": "",
        },
    )

    assert response.status_code == 422


def test_integration_context_endpoint_returns_context(
    client,
    monkeypatch,
):
    def fake_get_context(query):
        assert query == (
            "Entro en la taberna."
        )

        return {
            "campaign": {
                "id": 1,
                "name": "Campaña",
                "system": "D&D 5e 2014",
                "tone": "oscuro",
                "summary": "",
            },
            "session": None,
            "active_character": None,
            "query": "Entro en la taberna.",
            "context": {
                "query": "Entro en la taberna.",
                "context": "Sin información relevante.",
            },
        }

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.get_context",
        fake_get_context,
    )

    response = client.post(
        "/integration/context",
        json={
            "query": "Entro en la taberna.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["campaign"]["id"] == 1

    assert data["query"] == (
        "Entro en la taberna."
    )

    assert data["context"]["context"] == (
        "Sin información relevante."
    )


def test_integration_context_endpoint_returns_500_on_service_error(
    client,
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationServiceError,
    )

    def fake_get_context(query):
        raise SillyTavernIntegrationServiceError(
            "context failed"
        )

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.get_context",
        fake_get_context,
    )

    response = client.post(
        "/integration/context",
        json={
            "query": "Entro en la taberna.",
        },
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": "context failed"
    }


def test_integration_turn_endpoint_returns_processed_turn(
    client,
    monkeypatch,
):
    class FakeResult:
        narrative = (
            "La puerta se abre."
        )

        player_input = (
            "Abro la puerta."
        )

        operation_count = 0

        successful_operation_count = 0

        failed_operation_count = 0

        all_operations_succeeded = True

        world_changed = False

        operations = ()

        character_operations = ()

        operation_results = ()

    def fake_process_turn(
        player_input,
        narrative,
        external_turn_id=None,
        turn_version=1,
    ):
        assert player_input == (
            "Abro la puerta."
        )

        assert narrative == (
            "La puerta se abre."
        )

        assert turn_version == 1

        return FakeResult()

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.process_turn",
        fake_process_turn,
    )

    response = client.post(
        "/integration/turn",
        json={
            "player_input": "Abro la puerta.",
            "narrative": "La puerta se abre.",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["player_input"] == (
        "Abro la puerta."
    )

    assert data["narrative"] == (
        "La puerta se abre."
    )

    assert data["operation_count"] == 0

    assert data["successful_operation_count"] == 0

    assert data["failed_operation_count"] == 0

    assert data["all_operations_succeeded"] is True

    assert data["world_changed"] is False

    assert data["operations"] == []

    assert data["operation_results"] == []


def test_integration_turn_endpoint_returns_400_on_service_error(
    client,
    monkeypatch,
):
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationServiceError,
    )

    def fake_process_turn(
        player_input,
        narrative,
        external_turn_id=None,
        turn_version=1,
    ):
        raise SillyTavernIntegrationServiceError(
            "processing failed"
        )

    monkeypatch.setattr(
        "app.silly_tavern_integration_service.process_turn",
        fake_process_turn,
    )

    response = client.post(
        "/integration/turn",
        json={
            "player_input": "Abro la puerta.",
            "narrative": "La puerta se abre.",
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": "processing failed"
    }


# ============================================================
# SERVICE HELPERS
# ============================================================


def _build_service():
    from services.silly_tavern_integration_service import (
        SillyTavernIntegrationService,
    )
    from services.campaign_state_service import (
        CampaignStateService,
    )
    from services.context_builder import (
        ContextBuilder,
    )
    from services.llm_world_extractor import (
        LLMWorldExtractor,
    )
    from services.operation_parser import (
        OperationParser,
    )
    from services.world_service import (
        WorldService,
    )
    from repositories.turn_repository import (
        TurnRepository,
    )
    from repositories.campaign_repository import (
        CampaignRepository,
    )
    from repositories.character_repository import (
        CharacterRepository,
    )
    from repositories.entity_repository import (
        EntityRepository,
    )

    world_service = WorldService()

    campaign_state_service = (
        CampaignStateService(
            campaign_repository=(
                CampaignRepository()
            ),
            character_repository=(
                CharacterRepository()
            ),
            entity_repository=(
                EntityRepository()
            ),
            world_service=world_service,
        )
    )

    context_builder = ContextBuilder()

    extractor = LLMWorldExtractor(
        provider=lambda prompt: (
            '{"operations": []}'
        ),
        operation_parser=OperationParser(),
    )

    turn_repository = TurnRepository()

    service = (
        SillyTavernIntegrationService(
            campaign_state_service=(
                campaign_state_service
            ),
            context_builder=context_builder,
            extractor=extractor,
            world_service=world_service,
            turn_repository=turn_repository,
        )
    )

    return (
        service,
        context_builder,
        extractor,
        world_service,
        turn_repository,
    )


# ============================================================
# SERVICE - CONTEXT
# ============================================================


def test_integration_service_uses_context_builder_for_context(
    monkeypatch,
):
    (
        service,
        context_builder,
        _extractor,
        _world_service,
        turn_repository,
    ) = _build_service()

    calls = []

    def fake_build(
        world,
        query,
        recent_turns=None,
    ):
        calls.append(
            {
                "world": world,
                "query": query,
                "recent_turns": recent_turns,
            }
        )

        return {
            "query": query,
            "context": "CONTEXTO",
        }

    monkeypatch.setattr(
        context_builder,
        "build",
        fake_build,
    )

    result = service.get_context(
        "Entro en la taberna."
    )

    assert result["query"] == (
        "Entro en la taberna."
    )

    assert result["context"] == {
        "query": "Entro en la taberna.",
        "context": "CONTEXTO",
    }

    assert len(calls) == 1

    assert calls[0]["query"] == (
        "Entro en la taberna."
    )

    assert isinstance(
        calls[0]["recent_turns"],
        list,
    )


# ============================================================
# SERVICE - NARRATIVE
# ============================================================


def test_integration_service_does_not_generate_narrative(
    monkeypatch,
):
    (
        service,
        _context_builder,
        extractor,
        world_service,
        turn_repository,
    ) = _build_service()

    monkeypatch.setattr(
        extractor,
        "extract",
        lambda narrative, context: [],
    )

    monkeypatch.setattr(
        turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    monkeypatch.setattr(
        turn_repository,
        "save_turn",
        lambda turn, *, conn=None: turn,
    )

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        lambda world_operations,
        character_operations,
        *,
        conn=None,
        ordered_operations=None: (),
    )

    result = service.process_turn(
        player_input="Abro la puerta.",
        narrative="La puerta se abre.",
    )

    assert result.narrative == (
        "La puerta se abre."
    )


def test_integration_service_passes_silly_tavern_narrative_to_extractor(
    monkeypatch,
):
    (
        service,
        _context_builder,
        extractor,
        world_service,
        turn_repository,
    ) = _build_service()

    captured = {}

    def fake_extract(
        text,
        context,
    ):
        captured["text"] = text
        captured["context"] = context

        return []

    monkeypatch.setattr(
        extractor,
        "extract",
        fake_extract,
    )

    monkeypatch.setattr(
        turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    monkeypatch.setattr(
        turn_repository,
        "save_turn",
        lambda turn, *, conn=None: turn,
    )

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        lambda world_operations,
        character_operations,
        *,
        conn=None,
        ordered_operations=None: (),
    )

    result = service.process_turn(
        player_input="Abro la puerta.",
        narrative=(
            "La puerta se abre lentamente."
        ),
    )

    assert captured["text"] == (
        "La puerta se abre lentamente."
    )

    assert captured["context"] is not None

    assert result.narrative == (
        "La puerta se abre lentamente."
    )


# ============================================================
# SERVICE - OPERATIONS
# ============================================================


def test_integration_service_applies_extracted_operations(
    monkeypatch,
):
    (
        service,
        _context_builder,
        extractor,
        world_service,
        turn_repository,
    ) = _build_service()

    operations = []

    monkeypatch.setattr(
        extractor,
        "extract",
        lambda narrative, context: operations,
    )

    monkeypatch.setattr(
        turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    captured = {}

    def fake_apply_turn_operations(
        world_operations,
        character_operations,
        *,
        conn=None,
        ordered_operations=None,
    ):
        captured["world_operations"] = tuple(
            world_operations
        )

        captured["character_operations"] = tuple(
            character_operations
        )

        captured["ordered_operations"] = tuple(
            ordered_operations
        )

        captured["conn"] = conn

        return ()

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        fake_apply_turn_operations,
    )

    monkeypatch.setattr(
        turn_repository,
        "save_turn",
        lambda turn, *, conn=None: (
            captured.__setitem__(
                "save_conn",
                conn,
            )
            or turn
        ),
    )

    result = service.process_turn(
        player_input="Abro la puerta.",
        narrative="La puerta se abre.",
    )

    assert result.operation_count == 0

    assert captured["world_operations"] == ()

    assert captured["character_operations"] == ()

    assert captured["ordered_operations"] == ()

    assert captured["conn"] is not None

    assert captured["save_conn"] is (
        captured["conn"]
    )


# ============================================================
# SERVICE - OPERATION ORDER
# ============================================================

def test_integration_service_preserves_operation_order(
    monkeypatch,
):
    from operations.character_operations import (
        ChangeCharacterHpOperation,
    )
    from operations.referenced_operation import (
        ReferencedOperation,
    )
    from operations.world_operations import (
        CreateEntityOperation,
    )

    (
        service,
        _context_builder,
        extractor,
        world_service,
        turn_repository,
    ) = _build_service()

    # --------------------------------------------------------
    # Operaciones en el orden exacto producido por el extractor.
    #
    # World -> Character -> World
    # --------------------------------------------------------

    operation_a = ReferencedOperation(
        ref="first",
        operation=CreateEntityOperation(
            name="Aldren",
            entity_type="npc",
        ),
    )

    operation_b = ReferencedOperation(
        ref="second",
        operation=ChangeCharacterHpOperation(
            entity_id=1,
            amount=-2,
        ),
    )

    operation_c = ReferencedOperation(
        ref="third",
        operation=CreateEntityOperation(
            name="Marta",
            entity_type="npc",
        ),
    )

    operations = [
        operation_a,
        operation_b,
        operation_c,
    ]

    monkeypatch.setattr(
        extractor,
        "extract",
        lambda narrative, context: operations,
    )

    monkeypatch.setattr(
        turn_repository,
        "list_recent_turns",
        lambda session_id=None, limit=10: [],
    )

    captured = {}

    def fake_apply_turn_operations(
        world_operations,
        character_operations,
        *,
        conn=None,
        ordered_operations=None,
    ):
        captured["world_operations"] = tuple(
            world_operations
        )

        captured["character_operations"] = tuple(
            character_operations
        )

        captured["ordered_operations"] = tuple(
            ordered_operations
        )

        captured["conn"] = conn

        # Este test NO pretende probar el contenido de los
        # OperationResult. Solo necesitamos devolver tres
        # elementos para que el resultado del turno tenga
        # la misma cardinalidad que las operaciones.
        return (
            None,
            None,
            None,
        )

    monkeypatch.setattr(
        world_service,
        "apply_turn_operations",
        fake_apply_turn_operations,
    )

    monkeypatch.setattr(
        turn_repository,
        "save_turn",
        lambda turn, *, conn=None: turn,
    )

    service.process_turn(
        player_input="Hago algo.",
        narrative="Ocurre algo.",
    )

    # --------------------------------------------------------
    # Las operaciones siguen separadas por tipo.
    # --------------------------------------------------------

    assert captured["world_operations"] == (
        operation_a,
        operation_c,
    )

    assert captured["character_operations"] == (
        operation_b,
    )

    # --------------------------------------------------------
    # ESTA ES LA COMPROBACIÓN IMPORTANTE:
    #
    # El orden original producido por el extractor se conserva
    # aunque las operaciones se separen internamente por tipo.
    # --------------------------------------------------------

    assert captured["ordered_operations"] == (
        operation_a,
        operation_b,
        operation_c,
    )

    # --------------------------------------------------------
    # WorldService recibió una conexión.
    # --------------------------------------------------------

    assert captured["conn"] is not None

def test_regenerate_turn_restores_snapshot_and_allows_new_version(
    client,
    monkeypatch,
):
    from database import get_conn
    from operations.world_operations import (
        CreateItemInstanceOperation,
    )

    external_turn_id = "test-external-turn"

    # =========================================================
    # Usamos el extractor real del servicio de SillyTavern,
    # pero hacemos que devuelva operaciones deterministas.
    # Así el test NO depende de Ollama.
    # =========================================================

    service = __import__(
        "app"
    ).silly_tavern_integration_service

    create_instance_operation = (
        CreateItemInstanceOperation(
            item_id=16,
            instance_number=1,
            owner_id=10,
            condition="oxidado",
        )
    )

    monkeypatch.setattr(
        service.extractor,
        "extract",
        lambda narrative, context: (
            [create_instance_operation]
            if narrative == "Narrativa con espada."
            else []
        ),
    )

    # ---------------------------------------------------------
    # V1 - Primera generación
    # ---------------------------------------------------------

    response_v1 = client.post(
        "/integration/turn",
        json={
            "player_input": (
                "Cojo la espada oxidada "
                "y la guardo en mi inventario."
            ),
            "narrative": "Narrativa con espada.",
            "external_turn_id": external_turn_id,
            "turn_version": 1,
        },
    )

    assert response_v1.status_code == 200

    data_v1 = response_v1.json()

    assert data_v1["turn_version"] == 1
    assert data_v1["external_turn_id"] == (
        external_turn_id
    )

    assert data_v1["operation_count"] == 1
    assert data_v1["successful_operation_count"] == 1
    assert data_v1["failed_operation_count"] == 0
    assert data_v1["all_operations_succeeded"] is True
    assert data_v1["world_changed"] is True

    # ---------------------------------------------------------
    # Comprobamos que V1 creó la instancia.
    # ---------------------------------------------------------

    with get_conn() as conn:
        instance_v1 = conn.execute(
            """
            SELECT
                id,
                item_id,
                instance_number,
                owner_id,
                condition,
                active
            FROM item_instances
            WHERE item_id = 16
              AND owner_id = 10
            """
        ).fetchone()

        turns_v1 = conn.execute(
            """
            SELECT
                version,
                status,
                operation_count,
                world_changed,
                snapshot IS NOT NULL AS has_snapshot
            FROM turns
            WHERE external_turn_id = ?
            ORDER BY version
            """,
            (external_turn_id,),
        ).fetchall()

    assert instance_v1 is not None

    assert instance_v1["item_id"] == 16
    assert instance_v1["instance_number"] == 1
    assert instance_v1["owner_id"] == 10
    assert instance_v1["condition"] == "oxidado"
    assert instance_v1["active"] == 1

    assert len(turns_v1) == 1
    assert turns_v1[0]["version"] == 1
    assert turns_v1[0]["status"] == "active"
    assert turns_v1[0]["operation_count"] == 1
    assert turns_v1[0]["world_changed"] == 1
    assert turns_v1[0]["has_snapshot"] == 1

    # ---------------------------------------------------------
    # V2 - Regeneración
    #
    # Esta narrativa NO contiene "espada", por lo que el
    # extractor devuelve cero operaciones.
    #
    # Lo importante es que antes de procesar V2 el servicio
    # restaure el snapshot de V1.
    # ---------------------------------------------------------

    response_v2 = client.post(
        "/integration/turn",
        json={
            "player_input": (
                "Cojo la espada oxidada "
                "y la guardo en mi inventario."
            ),
            "narrative": "Narrativa alternativa.",
            "external_turn_id": external_turn_id,
            "turn_version": 2,
        },
    )

    assert response_v2.status_code == 200

    data_v2 = response_v2.json()

    assert data_v2["turn_version"] == 2
    assert data_v2["external_turn_id"] == (
        external_turn_id
    )

    assert data_v2["operation_count"] == 0
    assert data_v2["successful_operation_count"] == 0
    assert data_v2["failed_operation_count"] == 0
    assert data_v2["all_operations_succeeded"] is True
    assert data_v2["world_changed"] is False

    # ---------------------------------------------------------
    # V1 debe quedar superseded.
    # V2 debe quedar active.
    # ---------------------------------------------------------

    with get_conn() as conn:
        turns_v2 = conn.execute(
            """
            SELECT
                version,
                status,
                operation_count,
                world_changed,
                snapshot IS NOT NULL AS has_snapshot
            FROM turns
            WHERE external_turn_id = ?
            ORDER BY version
            """,
            (external_turn_id,),
        ).fetchall()

        instance_v2 = conn.execute(
            """
            SELECT id
            FROM item_instances
            WHERE item_id = 16
              AND owner_id = 10
            """
        ).fetchone()

    assert len(turns_v2) == 2

    assert turns_v2[0]["version"] == 1
    assert turns_v2[0]["status"] == "superseded"
    assert turns_v2[0]["operation_count"] == 1
    assert turns_v2[0]["has_snapshot"] == 1

    assert turns_v2[1]["version"] == 2
    assert turns_v2[1]["status"] == "active"
    assert turns_v2[1]["operation_count"] == 0
    assert turns_v2[1]["world_changed"] == 0
    assert turns_v2[1]["has_snapshot"] == 1

    # =========================================================
    # PUNTO CLAVE DEL TEST:
    #
    # La instancia creada por V1 debe haber desaparecido al
    # restaurar el snapshot.
    # =========================================================

    assert instance_v2 is None

    # ---------------------------------------------------------
    # V3 - Nueva regeneración
    #
    # Volvemos a usar la narrativa que genera la operación.
    # Esto prueba que después del rollback podemos aplicar
    # una nueva versión desde el estado restaurado.
    # ---------------------------------------------------------

    response_v3 = client.post(
        "/integration/turn",
        json={
            "player_input": (
                "Cojo la espada oxidada "
                "y la guardo en mi inventario."
            ),
            "narrative": "Narrativa con espada.",
            "external_turn_id": external_turn_id,
            "turn_version": 3,
        },
    )

    assert response_v3.status_code == 200

    data_v3 = response_v3.json()

    assert data_v3["turn_version"] == 3
    assert data_v3["external_turn_id"] == (
        external_turn_id
    )

    assert data_v3["operation_count"] == 1
    assert data_v3["successful_operation_count"] == 1
    assert data_v3["failed_operation_count"] == 0
    assert data_v3["all_operations_succeeded"] is True
    assert data_v3["world_changed"] is True

    # ---------------------------------------------------------
    # Estado final
    # ---------------------------------------------------------

    with get_conn() as conn:
        final_turns = conn.execute(
            """
            SELECT
                version,
                status,
                operation_count,
                world_changed,
                snapshot IS NOT NULL AS has_snapshot
            FROM turns
            WHERE external_turn_id = ?
            ORDER BY version
            """,
            (external_turn_id,),
        ).fetchall()

        final_instance = conn.execute(
            """
            SELECT
                id,
                item_id,
                instance_number,
                owner_id,
                condition,
                active
            FROM item_instances
            WHERE item_id = 16
              AND owner_id = 10
            """
        ).fetchone()

    assert len(final_turns) == 3

    # V1
    assert final_turns[0]["version"] == 1
    assert final_turns[0]["status"] == "superseded"
    assert final_turns[0]["operation_count"] == 1
    assert final_turns[0]["world_changed"] == 1
    assert final_turns[0]["has_snapshot"] == 1

    # V2
    assert final_turns[1]["version"] == 2
    assert final_turns[1]["status"] == "superseded"
    assert final_turns[1]["operation_count"] == 0
    assert final_turns[1]["world_changed"] == 0
    assert final_turns[1]["has_snapshot"] == 1

    # V3
    assert final_turns[2]["version"] == 3
    assert final_turns[2]["status"] == "active"
    assert final_turns[2]["operation_count"] == 1
    assert final_turns[2]["world_changed"] == 1
    assert final_turns[2]["has_snapshot"] == 1

    # La instancia vuelve a existir después de V3.
    assert final_instance is not None
    assert final_instance["item_id"] == 16
    assert final_instance["instance_number"] == 1
    assert final_instance["owner_id"] == 10
    assert final_instance["condition"] == "oxidado"
    assert final_instance["active"] == 1