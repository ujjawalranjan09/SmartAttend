import pytest
from httpx import AsyncClient

from app.core.security import create_refresh_token


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_admin):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_admin.email, "password": "Admin@1234"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"
    assert data["user_id"] == str(test_admin.id)


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "WrongPass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@test.com", "password": "AnyPass123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_admin):
    refresh_token = create_refresh_token(subject=str(test_admin.id))
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient, admin_headers, test_admin):
    response = await client.get(
        "/api/v1/auth/me",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_admin.email
    assert data["full_name"] == "Test Admin"
    assert data["role"] == "admin"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
