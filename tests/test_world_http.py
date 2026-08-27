from __future__ import annotations

from fastapi.testclient import TestClient
from models.operation_result import OperationResult, OperationStatus

from app import app

client = TestClient(app)

def test_world_operations_rejects_non_list_operations():
    client = TestClient(app)

    response = client.post(
        "/world/operations",
        json={
            "operations": "not-a-list",
        },
    )

    assert response.status_code == 422

def test_world_operations_accepts_empty_operations():
    client = TestClient(app)

    response = client.post(
        "/world/operations",
        json={
            "operations": [],
        },
    )

    assert response.status_code != 422

def test_world_operations_http_applies_valid_operations():
    client = TestClient(app)

    response = client.post(
        "/world/operations",
        json={
            "operations": [
                {
                    "type": "create_entity",
                    "name": "P2_1_HTTP_Valid_Entity",
                    "entity_type": "character",
                }
            ]
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["ok"] is True
    assert data["received"] == 1
    assert data["applied"] == 1
    assert data["results"][0]["status"] == "success"

def test_world_operations_http_does_not_report_success_when_apply_fails(
    monkeypatch,
):
    from app import world_service

    def fake_apply_operations_and_save(operations):
        return {
            "success": False,
            "results": [
                OperationResult(
                    status=OperationStatus.DUPLICATE,
                    message="Entity already exists.",
                )
            ],
        }

    monkeypatch.setattr(
        world_service,
        "apply_operations_and_save",
        fake_apply_operations_and_save,
    )

    response = client.post(
        "/world/operations",
        json={
            "operations": [
                {
                    "type": "create_entity",
                    "name": "Fungoso",
                    "entity_type": "character",
                }
            ]
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["ok"] is False
    assert body["received"] == 1
    assert body["applied"] == 0
    assert body["results"][0]["status"] == "duplicate"

def test_world_operations_returns_failure_when_operation_cannot_be_applied(
    monkeypatch,
):
    from app import world_service

    def fake_apply_operations_and_save(operations):
        return {
            "success": False,
            "results": [],
        }

    monkeypatch.setattr(
        world_service,
        "apply_operations_and_save",
        fake_apply_operations_and_save,
    )

    response = client.post(
        "/world/operations",
        json={
            "operations": [
                {
                    "type": "create_entity",
                    "name": "P1_6_Failing_Test",
                    "entity_type": "character",
                }
            ]
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["ok"] is False
    assert body["received"] == 1
    assert body["applied"] == 0
    assert body["results"] == []

def test_world_operations_returns_serializable_failure_response(
    monkeypatch,
):
    from app import world_service
    from models.operation_result import (
        OperationResult,
        OperationStatus,
    )

    def fake_apply_operations_and_save(operations):
        return {
            "success": False,
            "results": [
                OperationResult(
                    status=OperationStatus.DUPLICATE,
                    message="Entity 'Fungoso' already exists.",
                    operation=operations[0],
                )
            ],
        }

    monkeypatch.setattr(
        world_service,
        "apply_operations_and_save",
        fake_apply_operations_and_save,
    )

    response = client.post(
        "/world/operations",
        json={
            "operations": [
                {
                    "type": "create_entity",
                    "name": "Fungoso",
                    "entity_type": "character",
                }
            ]
        },
    )

    assert response.status_code == 400

    body = response.json()

    assert body["ok"] is False
    assert body["message"] == (
        "One or more operations could not be applied."
    )

    assert body["results"][0]["status"] == "duplicate"
    assert body["results"][0]["message"] == (
        "Entity 'Fungoso' already exists."
    )
    assert body["results"][0]["operation"] == "CreateEntityOperation"