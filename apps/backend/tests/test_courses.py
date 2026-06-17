import uuid

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


async def _make_student(db_session, test_institution, dept):
    student = User(
        id=uuid.uuid4(),
        email=f"student-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Enrolled Student",
        hashed_password=hash_password("Student@1234"),
        role=UserRole.STUDENT,
        institution_id=test_institution.id,
        department_id=dept.id,
        roll_number=f"STU-{uuid.uuid4().hex[:8]}",
        is_active=True,
        is_verified=True,
    )
    db_session.add(student)
    await db_session.flush()
    return student


@pytest.mark.asyncio
async def test_create_course_as_admin(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    response = await client.post(
        "/api/v1/courses/",
        json={
            "institution_id": str(test_institution.id),
            "department_id": str(dept.id),
            "faculty_id": str(uuid.uuid4()),
            "name": "Intro to CS",
            "code": "CS101",
            "semester": 1,
            "academic_year": "2025-26",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Intro to CS"
    assert data["code"] == "CS101"


@pytest.mark.asyncio
async def test_create_course_as_faculty_auto_sets_id(
    client: AsyncClient, faculty_headers, test_faculty, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    response = await client.post(
        "/api/v1/courses/",
        json={
            "institution_id": str(test_institution.id),
            "department_id": str(dept.id),
            "name": "Data Structures",
            "code": "CS201",
        },
        headers=faculty_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["faculty_id"] == str(test_faculty.id)


@pytest.mark.asyncio
async def test_list_courses_with_filters(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept1 = await _make_department(db_session, test_institution)
    dept2 = Department(
        id=uuid.uuid4(),
        institution_id=test_institution.id,
        name="Mathematics",
        code="MATH",
    )
    db_session.add(dept2)
    await db_session.flush()

    for name, code, dept in [
        ("CS1", "C1", dept1),
        ("CS2", "C2", dept1),
        ("MATH1", "M3", dept2),
    ]:
        db_session.add(
            Course(
                institution_id=test_institution.id,
                department_id=dept.id,
                faculty_id=uuid.uuid4(),
                name=name,
                code=code,
            )
        )
    await db_session.flush()

    response = await client.get(
        "/api/v1/courses/",
        params={"department_id": str(dept1.id)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2

    response = await client.get(
        "/api/v1/courses/",
        params={"department_id": str(dept2.id)},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 1


@pytest.mark.asyncio
async def test_enroll_students(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = Course(
        institution_id=test_institution.id,
        department_id=dept.id,
        faculty_id=uuid.uuid4(),
        name="Enroll Test",
        code="ET101",
    )
    db_session.add(course)
    await db_session.flush()

    s1 = await _make_student(db_session, test_institution, dept)
    s2 = await _make_student(db_session, test_institution, dept)

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll",
        json={"student_ids": [str(s1.id), str(s2.id)]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled"] == 2
    assert data["skipped"] == 0


@pytest.mark.asyncio
async def test_enroll_skips_duplicates(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = Course(
        institution_id=test_institution.id,
        department_id=dept.id,
        faculty_id=uuid.uuid4(),
        name="Dup Test",
        code="DT101",
    )
    db_session.add(course)
    await db_session.flush()

    student = await _make_student(db_session, test_institution, dept)

    await client.post(
        f"/api/v1/courses/{course.id}/enroll",
        json={"student_ids": [str(student.id)]},
        headers=admin_headers,
    )

    response = await client.post(
        f"/api/v1/courses/{course.id}/enroll",
        json={"student_ids": [str(student.id)]},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["enrolled"] == 0
    assert data["skipped"] == 1


@pytest.mark.asyncio
async def test_unenroll_student(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)
    course = Course(
        institution_id=test_institution.id,
        department_id=dept.id,
        faculty_id=uuid.uuid4(),
        name="Unenroll Test",
        code="UT101",
    )
    db_session.add(course)
    await db_session.flush()

    student = await _make_student(db_session, test_institution, dept)

    db_session.add(Enrollment(student_id=student.id, course_id=course.id))
    await db_session.flush()

    response = await client.delete(
        f"/api/v1/courses/{course.id}/enroll/{student.id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"removed": True}

    response = await client.delete(
        f"/api/v1/courses/{course.id}/enroll/{student.id}",
        headers=admin_headers,
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_faculty_cannot_update_other_course(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    dept = await _make_department(db_session, test_institution)

    faculty_a = User(
        id=uuid.uuid4(),
        email=f"fac-a-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Faculty A",
        hashed_password=hash_password("Fac@1234"),
        role=UserRole.FACULTY,
        institution_id=test_institution.id,
        is_active=True,
        is_verified=True,
    )
    faculty_b = User(
        id=uuid.uuid4(),
        email=f"fac-b-{uuid.uuid4().hex[:8]}@test.com",
        full_name="Faculty B",
        hashed_password=hash_password("Fac@1234"),
        role=UserRole.FACULTY,
        institution_id=test_institution.id,
        is_active=True,
        is_verified=True,
    )
    db_session.add_all([faculty_a, faculty_b])
    await db_session.flush()

    course = Course(
        institution_id=test_institution.id,
        department_id=dept.id,
        faculty_id=faculty_a.id,
        name="Owner Course",
        code="OC101",
    )
    db_session.add(course)
    await db_session.flush()

    from app.core.security import create_access_token

    token_b = create_access_token(
        subject=str(faculty_b.id),
        extra_claims={
            "role": faculty_b.role,
            "institution_id": str(faculty_b.institution_id),
        },
    )
    headers_b = {"Authorization": f"Bearer {token_b}"}

    response = await client.put(
        f"/api/v1/courses/{course.id}",
        json={"name": "Hacked Course"},
        headers=headers_b,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_course_not_found(client: AsyncClient, admin_headers):
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/courses/{fake_id}",
        headers=admin_headers,
    )
    assert response.status_code == 404
