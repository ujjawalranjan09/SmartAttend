import uuid
import io

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.models.institution import Department
from app.models.user import User, UserRole
from app.models.course import Course, Enrollment


async def _make_department(db_session, test_institution):
    dept = Department(
        id=uuid.uuid4(),
        institution_id=test_institution.id,
        name="Computer Science",
        code="CS",
    )
    db_session.add(dept)
    await db_session.flush()
    return dept


async def _make_course(db_session, test_institution, dept, faculty_id=None):
    course = Course(
        institution_id=test_institution.id,
        department_id=dept.id,
        faculty_id=faculty_id or uuid.uuid4(),
        name="CSV Enroll Course",
        code="CSV101",
    )
    db_session.add(course)
    await db_session.flush()
    return course


async def _make_student(
    db_session, test_institution, dept, email=None, roll_number=None
):
    student = User(
        id=uuid.uuid4(),
        email=email or f"student-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Test Student",
        hashed_password=hash_password("Student@1234"),
        role=UserRole.STUDENT,
        institution_id=test_institution.id,
        department_id=dept.id,
        roll_number=roll_number or f"STU-{uuid.uuid4().hex[:8]}",
        is_active=True,
        is_verified=True,
    )
    db_session.add(student)
    await db_session.flush()
    return student


def _csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b"email\n"
    header = ",".join(rows[0].keys())
    lines = [header] + [",".join(r.values()) for r in rows]
    return "\n".join(lines).encode("utf-8")


@pytest.mark.asyncio
async def test_enroll_csv_valid_emails(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = await _make_course(db_session, test_institution, dept)

    s1 = await _make_student(db_session, test_institution, dept, email="alice@test.com")
    s2 = await _make_student(db_session, test_institution, dept, email="bob@test.com")

    csv_content = _csv_bytes(
        [
            {"email": "alice@test.com"},
            {"email": "bob@test.com"},
        ]
    )

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled_count"] == 2
    assert data["skipped_count"] == 0
    assert data["not_found"] == []


@pytest.mark.asyncio
async def test_enroll_csv_unknown_emails(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = await _make_course(db_session, test_institution, dept)

    csv_content = _csv_bytes(
        [
            {"email": "ghost@test.com"},
        ]
    )

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled_count"] == 0
    assert data["not_found"] == ["ghost@test.com"]


@pytest.mark.asyncio
async def test_enroll_csv_skips_duplicates(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = await _make_course(db_session, test_institution, dept)

    student = await _make_student(
        db_session, test_institution, dept, email="dup@test.com"
    )

    await client.post(
        f"/api/v1/courses/{course.id}/enroll",
        json={"student_ids": [str(student.id)]},
        headers=admin_headers,
    )

    csv_content = _csv_bytes([{"email": "dup@test.com"}])

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled_count"] == 0
    assert data["skipped_count"] == 1


@pytest.mark.asyncio
async def test_enroll_csv_empty(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = await _make_course(db_session, test_institution, dept)

    csv_content = b"email"

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled_count"] == 0
    assert data["skipped_count"] == 0


@pytest.mark.asyncio
async def test_enroll_csv_course_not_found(client: AsyncClient, admin_headers):
    fake_id = uuid.uuid4()
    csv_content = _csv_bytes([{"email": "x@test.com"}])

    response = await client.post(
        f"/api/v1/courses/{fake_id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_enroll_csv_by_roll_number(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = await _make_course(db_session, test_institution, dept)

    student = await _make_student(
        db_session, test_institution, dept, roll_number="CS-1001"
    )

    csv_content = _csv_bytes([{"roll_number": "CS-1001"}])

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled_count"] == 1
    assert data["skipped_count"] == 0


@pytest.mark.asyncio
async def test_enroll_csv_invalid_format(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = await _make_course(db_session, test_institution, dept)

    csv_content = b"name,age\nAlice,20"

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll/csv",
        files={"upload_file": ("students.csv", csv_content, "text/csv")},
        headers=admin_headers,
    )
    assert response.status_code == 400
