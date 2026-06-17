import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_students_as_admin(
    client: AsyncClient, admin_headers, test_institution
):
    response = await client.get(
        "/api/v1/students/",
        params={"institution_id": str(test_institution.id)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_list_students_as_student(
    client: AsyncClient, student_headers, test_institution
):
    response = await client.get(
        "/api/v1/students/",
        params={"institution_id": str(test_institution.id)},
        headers=student_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_student_as_admin(
    client: AsyncClient, admin_headers, test_institution
):
    response = await client.post(
        "/api/v1/students/",
        json={
            "email": "newstudent@test.com",
            "full_name": "New Student",
            "password": "SecurePass123",
            "role": "student",
            "institution_id": str(test_institution.id),
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newstudent@test.com"
    assert data["full_name"] == "New Student"
    assert data["role"] == "student"


@pytest.mark.asyncio
async def test_create_student_duplicate_email(
    client: AsyncClient, admin_headers, test_institution, test_student
):
    response = await client.post(
        "/api/v1/students/",
        json={
            "email": test_student.email,
            "full_name": "Another Student",
            "password": "SecurePass123",
            "role": "student",
            "institution_id": str(test_institution.id),
        },
        headers=admin_headers,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_get_student_detail(client: AsyncClient, admin_headers, test_student):
    response = await client.get(
        f"/api/v1/students/{test_student.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_student.id)
    assert data["email"] == test_student.email
    assert data["full_name"] == "Test Student"
    assert data["role"] == "student"
