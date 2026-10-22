from fastapi.testclient import TestClient

from tests.conftest import create_test_jwt


def test_wellness_allowed_for_analyst(test_client: TestClient) -> None:
    token = create_test_jwt(roles=["dept_analyst"], groups=["/Departamentos/Preparacion-Fisica"])
    response = test_client.get(
        "/api/v1/wellness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_wellness_allowed_for_admin(test_client: TestClient) -> None:
    token = create_test_jwt(roles=["dept_admin"], groups=["/Departamentos/Direccion-Deportiva"])
    response = test_client.get(
        "/api/v1/wellness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_wellness_forbidden_for_ingestor_only(test_client: TestClient) -> None:
    token = create_test_jwt(roles=["dept_ingestor"], groups=["/Departamentos/Medico"])
    response = test_client.get(
        "/api/v1/wellness",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


def test_ingest_tableflow_m2m_allowed_for_authorized_department(test_client: TestClient) -> None:
    token = create_test_jwt(
        roles=["dept_ingestor"],
        groups=["/Departamentos/Medico"],
    )

    payload = {
        "club_id": "11111111-1111-1111-1111-111111111111",
        "department_id": "medico",
        "form_name": "injuries",
        "category_id": "22222222-2222-2222-2222-222222222201",
        "records": [
            {
                "player_id": "33333333-3333-3333-3333-333333333301",
                "metric_date": "2026-10-22",
                "data": {"severity": "low"},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_ingest_tableflow_m2m_forbidden_for_cross_department(test_client: TestClient) -> None:
    token = create_test_jwt(
        roles=["dept_ingestor"],
        groups=["/Departamentos/Medico"],
    )

    payload = {
        "club_id": "11111111-1111-1111-1111-111111111111",
        "department_id": "scouting",
        "form_name": "reports",
        "category_id": "22222222-2222-2222-2222-222222222201",
        "records": [
            {
                "player_id": "33333333-3333-3333-3333-333333333301",
                "metric_date": "2026-10-22",
                "data": {},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "not authorized for department" in response.json()["detail"]


def test_ingest_tableflow_admin_can_ingest_any_department(test_client: TestClient) -> None:
    token = create_test_jwt(
        roles=["dept_admin"],
        groups=["/Departamentos/Direccion-Deportiva"],
    )

    payload = {
        "club_id": "11111111-1111-1111-1111-111111111111",
        "department_id": "cantera",
        "form_name": "evaluations",
        "category_id": "22222222-2222-2222-2222-222222222201",
        "records": [
            {
                "player_id": "33333333-3333-3333-3333-333333333301",
                "metric_date": "2026-10-22",
                "data": {},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200


def test_ingest_tableflow_forbidden_for_analyst_role(test_client: TestClient) -> None:
    token = create_test_jwt(
        roles=["dept_analyst"],
        groups=["/Departamentos/Medico"],
    )

    payload = {
        "club_id": "11111111-1111-1111-1111-111111111111",
        "department_id": "medico",
        "form_name": "wellness",
        "category_id": "22222222-2222-2222-2222-222222222201",
        "records": [
            {
                "player_id": "33333333-3333-3333-3333-333333333301",
                "metric_date": "2026-10-22",
                "data": {},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403
    assert "dept_ingestor" in response.json()["detail"]


def test_ingest_tableflow_invalid_secret_header(test_client: TestClient) -> None:
    payload = {
        "club_id": "11111111-1111-1111-1111-111111111111",
        "department_id": "medico",
        "form_name": "wellness",
        "category_id": "22222222-2222-2222-2222-222222222201",
        "records": [
            {
                "player_id": "33333333-3333-3333-3333-333333333301",
                "metric_date": "2026-10-22",
                "data": {},
            }
        ],
    }

    response = test_client.post(
        "/api/v1/ingest/tableflow",
        json=payload,
        headers={"X-Tableflow-Secret": "wrong-secret-token"},
    )
    assert response.status_code == 401
