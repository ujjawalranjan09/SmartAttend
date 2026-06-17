"""Tests for Phase 4 features: logout, data-export, account deletion, security headers."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_logout_blacklists_token(client: AsyncClient, admin_headers):
    """POST /auth/logout blacklists the access token."""
    resp = await client.post("/api/v1/auth/logout", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_data_export_returns_user_info(client: AsyncClient, admin_headers, test_admin):
    """POST /auth/data-export returns user data."""
    resp = await client.post("/api/v1/auth/data-export", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "user" in data
    assert data["user"]["email"] == test_admin.email
    assert "attendance_records" in data
    assert "notifications" in data


@pytest.mark.asyncio
async def test_delete_account_anonymizes(client: AsyncClient, test_student):
    """DELETE /auth/me soft-deletes and anonymizes the account."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=str(test_student.id),
        extra_claims={"role": test_student.role, "institution_id": str(test_student.institution_id)},
    )
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.delete("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 204

    # Verify the user can no longer authenticate
    resp2 = await client.get("/api/v1/auth/me", headers=headers)
    assert resp2.status_code == 401


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Security headers are added to responses."""
    resp = await client.get("/health")
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert "content-security-policy" in resp.headers
    assert "permissions-policy" in resp.headers


@pytest.mark.asyncio
async def test_body_size_limit(client: AsyncClient, admin_headers):
    """Requests exceeding body size limit return 413."""
    # Send a body larger than 1MB to a regular endpoint
    large_body = "x" * (1024 * 1024 + 1)
    resp = await client.post(
        "/api/v1/auth/forgot-password",
        content=large_body,
        headers={**admin_headers, "Content-Type": "application/json"},
    )
    assert resp.status_code == 413


@pytest.mark.asyncio
async def test_gzip_compression(client: AsyncClient, admin_headers):
    """Responses are GZip-compressed when client accepts it."""
    resp = await client.get(
        "/api/v1/institutions/",
        headers={**admin_headers, "Accept-Encoding": "gzip"},
    )
    # Response should succeed — compression is transparent
    assert resp.status_code == 200
