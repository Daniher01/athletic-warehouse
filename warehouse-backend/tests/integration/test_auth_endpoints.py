from fastapi.testclient import TestClient

from tests.conftest import create_test_jwt


def test_auth_me_authenticated_user(test_client: TestClient) -> None:
    token = create_test_jwt(
        sub="user-garcia-id",
        username="dr_garcia",
        roles=["dept_ingestor"],
        groups=["/Departamentos/Medico"],
    )

    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == "user-garcia-id"
    assert data["username"] == "dr_garcia"
    assert data["email"] == "dr_garcia@example.com"
    assert "dept_ingestor" in data["roles"]
    assert "medico" in data["departments"]
    assert "/Departamentos/Medico" in data["groups"]
    assert data["is_admin"] is False


def test_auth_me_admin_user(test_client: TestClient) -> None:
    token = create_test_jwt(
        sub="admin-id",
        username="admin_user",
        roles=["dept_admin"],
        groups=["/Departamentos/Direccion-Deportiva"],
    )

    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True


def test_auth_me_missing_token(test_client: TestClient) -> None:
    response = test_client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert "credentials were not provided" in response.json()["detail"]


def test_auth_me_expired_token(test_client: TestClient) -> None:
    token = create_test_jwt(expires_in_seconds=-100)
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


def test_auth_me_malformed_token(test_client: TestClient) -> None:
    response = test_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-valid-jwt-token"},
    )
    assert response.status_code == 401
