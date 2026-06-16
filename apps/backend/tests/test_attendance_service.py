import uuid
import math

import pytest

from app.services.attendance_service import AttendanceService


@pytest.fixture
def att_svc(db_session):
    return AttendanceService(db_session)


def test_haversine_same_point(att_svc):
    distance = att_svc._haversine_distance(28.6139, 77.2090, 28.6139, 77.2090)
    assert distance == pytest.approx(0.0, abs=0.01)


def test_haversine_known_distance(att_svc):
    lat1, lon1 = 0.0, 0.0
    lat2, lon2 = 0.0, 1.0
    distance = att_svc._haversine_distance(lat1, lon1, lat2, lon2)
    assert distance == pytest.approx(111_320, rel=0.01)


@pytest.mark.asyncio
async def test_get_by_session_empty(att_svc):
    records = await att_svc.get_by_session(uuid.uuid4())
    assert records == []
