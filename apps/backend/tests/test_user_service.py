import uuid

import pytest

from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


@pytest.fixture
def user_svc(db_session):
    return UserService(db_session)


def _make_user_data(email="test@example.com", **overrides):
    defaults = dict(
        email=email,
        full_name="Test User",
        password="SecurePass123",
        role=UserRole.STUDENT,
    )
    defaults.update(overrides)
    return UserCreate(**defaults)


@pytest.mark.asyncio
async def test_create_user(user_svc):
    data = _make_user_data(
        email="new@test.com",
        full_name="New Student",
        role=UserRole.STUDENT,
        roll_number="STU100",
    )
    user = await user_svc.create(data)
    assert user.id is not None
    assert user.email == "new@test.com"
    assert user.full_name == "New Student"
    assert user.role == UserRole.STUDENT
    assert user.roll_number == "STU100"
    assert user.is_active is True
    assert user.hashed_password != "SecurePass123"


@pytest.mark.asyncio
async def test_get_by_email(user_svc):
    data = _make_user_data(email="lookup@test.com", full_name="Lookup User")
    created = await user_svc.create(data)
    found = await user_svc.get_by_email("lookup@test.com")
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_get_by_email_not_found(user_svc):
    found = await user_svc.get_by_email("nonexistent@test.com")
    assert found is None


@pytest.mark.asyncio
async def test_get_by_id(user_svc):
    data = _make_user_data(email="byid@test.com", full_name="By ID User")
    created = await user_svc.create(data)
    found = await user_svc.get_by_id(created.id)
    assert found is not None
    assert found.email == "byid@test.com"


@pytest.mark.asyncio
async def test_update_user(user_svc):
    data = _make_user_data(email="update@test.com", full_name="Original Name")
    created = await user_svc.create(data)
    update_data = UserUpdate(full_name="Updated Name", phone="555-0100")
    updated = await user_svc.update(created.id, update_data)
    assert updated is not None
    assert updated.full_name == "Updated Name"
    assert updated.phone == "555-0100"


@pytest.mark.asyncio
async def test_deactivate_user(user_svc):
    data = _make_user_data(email="deact@test.com", full_name="Deactivate User")
    created = await user_svc.create(data)
    result = await user_svc.deactivate(created.id)
    assert result is True
    refreshed = await user_svc.get_by_id(created.id)
    assert refreshed.is_active is False


@pytest.mark.asyncio
async def test_bulk_create(user_svc):
    users_data = [
        _make_user_data(email=f"bulk{i}@test.com", full_name=f"Bulk User {i}")
        for i in range(3)
    ]
    result = await user_svc.bulk_create(users_data)
    assert result["created"] == 3
    assert result["failed"] == 0
    assert result["errors"] == []
