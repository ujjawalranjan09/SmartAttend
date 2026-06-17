import uuid
from datetime import date, time, timedelta

import pytest
from httpx import AsyncClient

from app.models.institution import Department
from app.models.course import Course
from app.models.session import TimetableSlot, ClassSession, SessionStatus


async def _make_course(db_session, test_institution):
    dept = Department(
        id=uuid.uuid4(),
        institution_id=test_institution.id,
        name="Computer Science",
        code="CS",
    )
    db_session.add(dept)
    await db_session.flush()

    course = Course(
        id=uuid.uuid4(),
        institution_id=test_institution.id,
        department_id=dept.id,
        faculty_id=uuid.uuid4(),
        name="Intro to CS",
        code="CS101",
    )
    db_session.add(course)
    await db_session.flush()
    return course


def _next_monday():
    today = date.today()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    return today + timedelta(days=days_until_monday)


@pytest.mark.asyncio
async def test_create_slot(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    course = await _make_course(db_session, test_institution)
    response = await client.post(
        "/api/v1/timetable/slots",
        json={
            "course_id": str(course.id),
            "day_of_week": 0,
            "start_time": "09:00",
            "end_time": "10:00",
            "room": "A101",
            "building": "Main Block",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["course_id"] == str(course.id)
    assert data["day_of_week"] == 0
    assert data["room"] == "A101"
    assert data["building"] == "Main Block"
    assert "id" in data


@pytest.mark.asyncio
async def test_generate_sessions(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    course = await _make_course(db_session, test_institution)

    slot_ids = []
    for day in [0, 2]:
        slot = TimetableSlot(
            course_id=course.id,
            day_of_week=day,
            start_time=time(9, 0),
            end_time=time(10, 0),
        )
        db_session.add(slot)
        await db_session.flush()
        slot_ids.append(slot.id)

    next_monday = _next_monday()

    response = await client.post(
        "/api/v1/timetable/generate",
        params={"week_start": next_monday.isoformat()},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sessions_created"] == 2


@pytest.mark.asyncio
async def test_generate_skips_duplicates(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    course = await _make_course(db_session, test_institution)

    slot = TimetableSlot(
        course_id=course.id,
        day_of_week=1,
        start_time=time(10, 0),
        end_time=time(11, 0),
    )
    db_session.add(slot)
    await db_session.flush()

    next_monday = _next_monday()

    resp1 = await client.post(
        "/api/v1/timetable/generate",
        params={"week_start": next_monday.isoformat()},
        headers=admin_headers,
    )
    assert resp1.json()["sessions_created"] == 1

    resp2 = await client.post(
        "/api/v1/timetable/generate",
        params={"week_start": next_monday.isoformat()},
        headers=admin_headers,
    )
    assert resp2.json()["sessions_created"] == 0


@pytest.mark.asyncio
async def test_weekly_view(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    course = await _make_course(db_session, test_institution)

    slot = TimetableSlot(
        course_id=course.id,
        day_of_week=0,
        start_time=time(9, 0),
        end_time=time(10, 0),
        room="B202",
    )
    db_session.add(slot)
    await db_session.flush()

    next_monday = _next_monday()

    await client.post(
        "/api/v1/timetable/generate",
        params={"week_start": next_monday.isoformat()},
        headers=admin_headers,
    )

    response = await client.get(
        "/api/v1/timetable/weekly",
        params={
            "institution_id": str(test_institution.id),
            "week_start": next_monday.isoformat(),
        },
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["days"]) == 7
    monday_slots = data["days"][0]["slots"]
    assert len(monday_slots) == 1
    assert monday_slots[0]["room"] == "B202"


@pytest.mark.asyncio
async def test_update_slot(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    course = await _make_course(db_session, test_institution)

    create_resp = await client.post(
        "/api/v1/timetable/slots",
        json={
            "course_id": str(course.id),
            "day_of_week": 3,
            "start_time": "14:00",
            "end_time": "15:00",
            "room": "C303",
        },
        headers=admin_headers,
    )
    slot_id = create_resp.json()["id"]

    response = await client.put(
        f"/api/v1/timetable/slots/{slot_id}",
        json={"room": "D404"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["room"] == "D404"


@pytest.mark.asyncio
async def test_delete_slot(
    client: AsyncClient, admin_headers, test_institution, db_session
):
    course = await _make_course(db_session, test_institution)

    create_resp = await client.post(
        "/api/v1/timetable/slots",
        json={
            "course_id": str(course.id),
            "day_of_week": 5,
            "start_time": "11:00",
            "end_time": "12:00",
        },
        headers=admin_headers,
    )
    slot_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/timetable/slots/{slot_id}",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"deleted": True}
