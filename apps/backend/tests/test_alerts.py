import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from app.models.alert import Alert, AlertType, AlertSeverity


async def _create_alert(db_session, institution_id, student_id, **kwargs):
    alert = Alert(
        id=uuid.uuid4(),
        institution_id=institution_id,
        student_id=student_id,
        alert_type=kwargs.get("alert_type", AlertType.LOW_ATTENDANCE),
        severity=kwargs.get("severity", AlertSeverity.MEDIUM),
        message=kwargs.get("message", "Low attendance detected"),
        is_resolved=kwargs.get("is_resolved", False),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(alert)
    await db_session.flush()
    return alert


@pytest.mark.asyncio
async def test_faculty_can_list_institution_alerts(
    client: AsyncClient,
    faculty_headers,
    test_faculty,
    test_institution,
    test_student,
    db_session,
):
    alert = await _create_alert(db_session, test_institution.id, test_student.id)
    response = await client.get(
        "/api/v1/alerts/",
        headers=faculty_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    ids = [item["id"] for item in data["items"]]
    assert str(alert.id) in ids


@pytest.mark.asyncio
async def test_student_sees_only_own_alerts(
    client: AsyncClient,
    student_headers,
    test_student,
    test_faculty,
    test_institution,
    db_session,
):
    own_alert = await _create_alert(db_session, test_institution.id, test_student.id)
    other_alert = await _create_alert(db_session, test_institution.id, test_faculty.id)
    response = await client.get(
        "/api/v1/alerts/",
        headers=student_headers,
    )
    assert response.status_code == 200
    data = response.json()
    ids = [item["id"] for item in data["items"]]
    assert str(own_alert.id) in ids
    assert str(other_alert.id) not in ids


@pytest.mark.asyncio
async def test_resolve_alert(
    client: AsyncClient,
    faculty_headers,
    test_faculty,
    test_institution,
    test_student,
    db_session,
):
    alert = await _create_alert(db_session, test_institution.id, test_student.id)
    response = await client.patch(
        f"/api/v1/alerts/{alert.id}/resolve",
        headers=faculty_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_resolved"] is True
    assert data["resolved_by_id"] == str(test_faculty.id)
    assert data["resolved_at"] is not None


@pytest.mark.asyncio
async def test_cannot_resolve_already_resolved(
    client: AsyncClient,
    faculty_headers,
    test_faculty,
    test_institution,
    test_student,
    db_session,
):
    alert = await _create_alert(db_session, test_institution.id, test_student.id)
    resp1 = await client.patch(
        f"/api/v1/alerts/{alert.id}/resolve",
        headers=faculty_headers,
    )
    assert resp1.status_code == 200

    resp2 = await client.patch(
        f"/api/v1/alerts/{alert.id}/resolve",
        headers=faculty_headers,
    )
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_get_alert_not_found(
    client: AsyncClient,
    faculty_headers,
):
    fake_id = uuid.uuid4()
    response = await client.get(
        f"/api/v1/alerts/{fake_id}",
        headers=faculty_headers,
    )
    assert response.status_code == 404
