import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_department_as_admin(
    client: AsyncClient, admin_headers: dict, test_institution
):
    response = await client.post(
        "/api/v1/departments/",
        headers=admin_headers,
        json={
            "institution_id": str(test_institution.id),
            "name": "Computer Science",
            "code": "CS",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Computer Science"
    assert data["code"] == "CS"
    assert data["institution_id"] == str(test_institution.id)
    assert "id" in data


@pytest.mark.asyncio
async def test_create_department_duplicate_code_same_institution(
    client: AsyncClient, admin_headers: dict, test_institution
):
    payload = {
        "institution_id": str(test_institution.id),
        "name": "Mathematics",
        "code": "MATH",
    }
    r1 = await client.post("/api/v1/departments/", headers=admin_headers, json=payload)
    assert r1.status_code == 201

    r2 = await client.post("/api/v1/departments/", headers=admin_headers, json=payload)
    assert r2.status_code == 409


@pytest.mark.asyncio
async def test_create_department_same_code_different_institution(
    client: AsyncClient, admin_headers: dict, db_session, test_institution
):
    from app.models.institution import Institution
    from datetime import datetime, timezone

    inst2 = Institution(
        id=uuid.uuid4(),
        name="Second University",
        short_name=f"SU-{uuid.uuid4().hex[:8]}",
        city="City2",
        state="State2",
        country="Testia",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(inst2)
    await db_session.flush()

    payload = {
        "name": "Physics",
        "code": "PHY",
    }

    r1 = await client.post(
        "/api/v1/departments/",
        headers=admin_headers,
        json={**payload, "institution_id": str(test_institution.id)},
    )
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/departments/",
        headers=admin_headers,
        json={**payload, "institution_id": str(inst2.id)},
    )
    assert r2.status_code == 201


@pytest.mark.asyncio
async def test_list_departments_by_institution(
    client: AsyncClient, admin_headers: dict, test_institution
):
    for code, name in [("CS", "Comp Sci"), ("EE", "Electrical")]:
        await client.post(
            "/api/v1/departments/",
            headers=admin_headers,
            json={
                "institution_id": str(test_institution.id),
                "name": name,
                "code": code,
            },
        )

    response = await client.get(
        "/api/v1/departments/",
        headers=admin_headers,
        params={"institution_id": str(test_institution.id)},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_create_department_as_student_forbidden(
    client: AsyncClient, student_headers: dict, test_institution
):
    response = await client.post(
        "/api/v1/departments/",
        headers=student_headers,
        json={
            "institution_id": str(test_institution.id),
            "name": "Biology",
            "code": "BIO",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_department(
    client: AsyncClient, admin_headers: dict, test_institution
):
    create = await client.post(
        "/api/v1/departments/",
        headers=admin_headers,
        json={
            "institution_id": str(test_institution.id),
            "name": "Old Name",
            "code": "OLD",
        },
    )
    dept_id = create.json()["id"]

    response = await client.put(
        f"/api/v1/departments/{dept_id}",
        headers=admin_headers,
        json={"name": "New Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["code"] == "OLD"


@pytest.mark.asyncio
async def test_get_department_not_found(client: AsyncClient, admin_headers: dict):
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/departments/{fake_id}",
        headers=admin_headers,
    )
    assert response.status_code == 404
