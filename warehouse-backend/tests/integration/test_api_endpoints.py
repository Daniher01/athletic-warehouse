from fastapi.testclient import TestClient

from tests.conftest import create_test_jwt


def test_health_endpoint(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["warehouse_connected"] is True


def test_ingest_tableflow_with_secret_header(test_client: TestClient) -> None:
    club_id = "11111111-1111-1111-1111-111111111111"
    category_id = "22222222-2222-2222-2222-222222222201"
    player_id = "33333333-3333-3333-3333-333333333301"

    payload = {
        "club_id": club_id,
        "department_id": "preparacion-fisica",
        "form_name": "wellness",
        "category_id": category_id,
        "records": [
            {
                "player_id": player_id,
                "metric_date": "2026-10-22",
                "data": {"rpe": 8, "sleep_quality": 7},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"X-Tableflow-Secret": "tableflow-webhook-dev-secret"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["records_processed"] == 1
    assert data["records_inserted"] == 1
    assert data["players_provisioned"] == 0


def test_ingest_tableflow_with_m2m_bearer_token(test_client: TestClient) -> None:
    token = create_test_jwt(
        sub="tableflow-service-account",
        username="tableflow-m2m",
        roles=["dept_ingestor"],
        groups=["/Departamentos/Preparacion-Fisica"],
    )

    club_id = "11111111-1111-1111-1111-111111111111"
    category_id = "22222222-2222-2222-2222-222222222201"
    player_id = "33333333-3333-3333-3333-333333333301"

    payload = {
        "club_id": club_id,
        "department_id": "preparacion-fisica",
        "form_name": "wellness",
        "category_id": category_id,
        "records": [
            {
                "player_id": player_id,
                "metric_date": "2026-10-22",
                "data": {"rpe": 9},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "success"


def test_ingest_tableflow_forbidden_department(test_client: TestClient) -> None:
    # User is in Medico, attempting to ingest for Preparacion-Fisica
    token = create_test_jwt(
        sub="medico-user",
        username="dr_garcia",
        roles=["dept_ingestor"],
        groups=["/Departamentos/Medico"],
    )

    club_id = "11111111-1111-1111-1111-111111111111"
    category_id = "22222222-2222-2222-2222-222222222201"
    player_id = "33333333-3333-3333-3333-333333333301"

    payload = {
        "club_id": club_id,
        "department_id": "preparacion-fisica",
        "form_name": "wellness",
        "category_id": category_id,
        "records": [{"player_id": player_id, "metric_date": "2026-10-22", "data": {}}],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "Forbidden" in response.json()["detail"]


def test_ingest_tableflow_missing_auth_rejected(test_client: TestClient) -> None:
    club_id = "11111111-1111-1111-1111-111111111111"
    category_id = "22222222-2222-2222-2222-222222222201"
    player_id = "33333333-3333-3333-3333-333333333301"

    payload = {
        "club_id": club_id,
        "department_id": "preparacion-fisica",
        "form_name": "wellness",
        "category_id": category_id,
        "records": [{"player_id": player_id, "metric_date": "2026-10-22", "data": {}}],
    }

    response = test_client.post("/api/v1/ingest/tableflow", json=payload)
    assert response.status_code == 401


def test_ingest_tableflow_missing_player_id_rejected(test_client: TestClient) -> None:
    club_id = "11111111-1111-1111-1111-111111111111"
    category_id = "22222222-2222-2222-2222-222222222201"

    # Missing player_id in record
    payload = {
        "club_id": club_id,
        "department_id": "preparacion-fisica",
        "form_name": "wellness",
        "category_id": category_id,
        "records": [
            {
                "metric_date": "2026-10-22",
                "data": {"rpe": 8},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"X-Tableflow-Secret": "tableflow-webhook-dev-secret"},
    )
    assert response.status_code == 422


def test_list_wellness_endpoint_with_auth(test_client: TestClient) -> None:
    token = create_test_jwt(
        sub="analyst-user",
        username="coach_mikel",
        roles=["dept_analyst"],
        groups=["/Departamentos/Preparacion-Fisica"],
    )
    response = test_client.get(
        "/api/v1/wellness?limit=10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_wellness_endpoint_unauthorized(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/wellness?limit=10")
    assert response.status_code == 401
