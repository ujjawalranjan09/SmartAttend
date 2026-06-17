import pytest

pytestmark = pytest.mark.asyncio


async def test_create_institution_as_admin(client, admin_headers):
    payload = {
        "name": "New University",
        "short_name": "NU",
        "city": "Mumbai",
        "state": "MH",
        "country": "India",
    }
    resp = await client.post(
        "/api/v1/institutions/", json=payload, headers=admin_headers
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New University"
    assert data["short_name"] == "NU"
    assert "id" in data


async def test_create_institution_duplicate_short_name(client, admin_headers):
    payload = {
        "name": "Dup University",
        "short_name": "DUP",
    }
    resp1 = await client.post(
        "/api/v1/institutions/", json=payload, headers=admin_headers
    )
    assert resp1.status_code == 201

    payload2 = {"name": "Dup University 2", "short_name": "DUP"}
    resp2 = await client.post(
        "/api/v1/institutions/", json=payload2, headers=admin_headers
    )
    assert resp2.status_code == 409


async def test_create_institution_as_student_forbidden(client, student_headers):
    payload = {"name": "Forbidden Uni", "short_name": "FU"}
    resp = await client.post(
        "/api/v1/institutions/", json=payload, headers=student_headers
    )
    assert resp.status_code == 403


async def test_list_institutions(client, admin_headers, test_institution):
    for i in range(2):
        await client.post(
            "/api/v1/institutions/",
            json={"name": f"ListUni{i}", "short_name": f"LU{i}"},
            headers=admin_headers,
        )
    resp = await client.get("/api/v1/institutions/", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 2


async def test_get_institution(client, admin_headers, test_institution):
    resp = await client.get(
        f"/api/v1/institutions/{test_institution.id}", headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == str(test_institution.id)
    assert data["name"] == test_institution.name
    assert data["short_name"] == test_institution.short_name


async def test_update_institution(client, admin_headers, test_institution):
    resp = await client.put(
        f"/api/v1/institutions/{test_institution.id}",
        json={"name": "Updated University"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated University"
    assert data["short_name"] == test_institution.short_name


async def test_get_institution_not_found(client, admin_headers):
    from uuid import uuid4

    resp = await client.get(f"/api/v1/institutions/{uuid4()}", headers=admin_headers)
    assert resp.status_code == 404
