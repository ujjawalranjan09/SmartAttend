"""Tests for Student Profile & Goals API (Phase 6 Feature 1)."""
import uuid
from datetime import date, datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from app.models.student_profile import StudentProfile
from app.models.student_goal import StudentGoal


class TestProfileAPI:
    """Profile endpoints: GET /me/profile, POST /me/profile, PUT /me/profile."""

    @pytest.mark.asyncio
    async def test_create_profile_returns_201(self, client, student_headers):
        """POST /me/profile creates a profile and returns 201."""
        response = await client.post(
            "/api/v1/students/me/profile",
            json={
                "interests": ["machine learning", "web dev"],
                "strengths": ["mathematics", "programming"],
                "career_goals": ["software engineer"],
                "preferred_study_style": "hands-on",
                "daily_study_hours_target": 3,
            },
            headers=student_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["interests"] == ["machine learning", "web dev"]
        assert data["daily_study_hours_target"] == 3

    @pytest.mark.asyncio
    async def test_create_profile_duplicate_returns_409(self, client, student_headers, db_session, test_student):
        """POST /me/profile on existing profile returns 409."""
        # Create first profile
        db_session.add(StudentProfile(
            id=uuid.uuid4(),
            user_id=test_student.id,
            interests=["ml"],
            strengths=["math"],
            career_goals=["engineer"],
            daily_study_hours_target=2,
        ))
        await db_session.flush()

        response = await client.post(
            "/api/v1/students/me/profile",
            json={"interests": ["new interest"]},
            headers=student_headers,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_get_profile_returns_data(self, client, student_headers, db_session, test_student):
        """GET /me/profile returns profile data."""
        db_session.add(StudentProfile(
            id=uuid.uuid4(),
            user_id=test_student.id,
            interests=["data science"],
            strengths=["stats"],
            career_goals=["data analyst"],
            preferred_study_style="reading",
            daily_study_hours_target=4,
        ))
        await db_session.flush()

        response = await client.get("/api/v1/students/me/profile", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["interests"] == ["data science"]
        assert data["preferred_study_style"] == "reading"

    @pytest.mark.asyncio
    async def test_get_profile_not_found_returns_404(self, client, student_headers):
        """GET /me/profile when no profile exists returns 404."""
        response = await client.get("/api/v1/students/me/profile", headers=student_headers)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_profile_replaces_lists(self, client, student_headers, db_session, test_student):
        """PUT /me/profile replaces list fields, updates scalars."""
        db_session.add(StudentProfile(
            id=uuid.uuid4(),
            user_id=test_student.id,
            interests=["old interest"],
            strengths=["old strength"],
            career_goals=["old goal"],
            daily_study_hours_target=1,
        ))
        await db_session.flush()

        response = await client.put(
            "/api/v1/students/me/profile",
            json={
                "interests": ["new interest", "another"],
                "daily_study_hours_target": 5,
            },
            headers=student_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["interests"] == ["new interest", "another"]
        assert data["strengths"] == ["old strength"]  # unchanged
        assert data["daily_study_hours_target"] == 5


class TestGoalsAPI:
    """Goal endpoints: list, create, get, update, progress, delete."""

    @pytest.mark.asyncio
    async def test_create_goal_returns_201(self, client, student_headers):
        """POST /me/goals creates a goal and returns 201."""
        response = await client.post(
            "/api/v1/students/me/goals",
            json={
                "title": "Complete ML Course",
                "description": "Finish Andrew Ng's course",
                "category": "academic",
                "priority": "high",
                "target_date": "2026-07-01",
                "estimated_hours": 40,
                "milestones": [
                    {"title": "Week 1-3", "completed": False},
                    {"title": "Week 4-6", "completed": False},
                ],
            },
            headers=student_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Complete ML Course"
        assert data["status"] == "active"
        assert data["priority"] == "high"
        assert len(data["milestones"]) == 2

    @pytest.mark.asyncio
    async def test_list_goals_returns_only_active_by_default(self, client, student_headers, db_session, test_student):
        """GET /me/goals returns only active goals by default."""
        db_session.add(StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Active Goal", category="skill", status="active", priority="high",
        ))
        db_session.add(StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Completed Goal", category="skill", status="completed", priority="medium",
        ))
        await db_session.flush()

        response = await client.get("/api/v1/students/me/goals", headers=student_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Active Goal"

    @pytest.mark.asyncio
    async def test_list_goals_filter_by_status(self, client, student_headers, db_session, test_student):
        """GET /me/goals?status=completed returns completed goals."""
        db_session.add(StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Active", category="academic", status="active", priority="high",
        ))
        db_session.add(StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Completed", category="academic", status="completed", priority="medium",
        ))
        await db_session.flush()

        response = await client.get(
            "/api/v1/students/me/goals?status=completed",
            headers=student_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["title"] == "Completed"

    @pytest.mark.asyncio
    async def test_update_goal_works_for_owner(self, client, student_headers, db_session, test_student):
        """PUT /me/goals/{id} updates goal fields for owner."""
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Old Title", category="academic", status="active", priority="low",
        )
        db_session.add(goal)
        await db_session.flush()

        response = await client.put(
            f"/api/v1/students/me/goals/{goal.id}",
            json={"title": "New Title", "priority": "high"},
            headers=student_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"
        assert data["priority"] == "high"

    @pytest.mark.asyncio
    async def test_progress_update_increments_hours(self, client, student_headers, db_session, test_student):
        """PATCH /me/goals/{id}/progress increments completed_hours."""
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Study Goal", category="skill", status="active",
            completed_hours=5, estimated_hours=20,
        )
        db_session.add(goal)
        await db_session.flush()

        response = await client.patch(
            f"/api/v1/students/me/goals/{goal.id}/progress",
            json={"completed_hours": 2},
            headers=student_headers,
        )
        assert response.status_code == 200
        assert response.json()["completed_hours"] == 7

    @pytest.mark.asyncio
    async def test_progress_update_milestone_index(self, client, student_headers, db_session, test_student):
        """PATCH with milestone_index marks that milestone done."""
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Multi-step Goal", category="project", status="active",
            milestones=[
                {"title": "Step 1", "completed": False},
                {"title": "Step 2", "completed": False},
            ],
        )
        db_session.add(goal)
        await db_session.flush()

        response = await client.patch(
            f"/api/v1/students/me/goals/{goal.id}/progress",
            json={"completed_hours": 1, "milestone_index": 0},
            headers=student_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["milestones"][0]["completed"] is True
        assert data["milestones"][1]["completed"] is False

    @pytest.mark.asyncio
    async def test_all_milestones_completed_auto_sets_status(self, client, student_headers, db_session, test_student):
        """When all milestones are done, status auto-sets to 'completed'."""
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Finish Project", category="project", status="active",
            milestones=[
                {"title": "Phase 1", "completed": False},
                {"title": "Phase 2", "completed": False},
            ],
        )
        db_session.add(goal)
        await db_session.flush()

        # Mark first milestone
        await client.patch(
            f"/api/v1/students/me/goals/{goal.id}/progress",
            json={"completed_hours": 1, "milestone_index": 0},
            headers=student_headers,
        )
        # Mark second milestone
        response = await client.patch(
            f"/api/v1/students/me/goals/{goal.id}/progress",
            json={"completed_hours": 1, "milestone_index": 1},
            headers=student_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_delete_goal_soft_deletes(self, client, student_headers, db_session, test_student):
        """DELETE sets status to 'abandoned' (soft delete)."""
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Abandoned Goal", category="career", status="active",
        )
        db_session.add(goal)
        await db_session.flush()

        response = await client.delete(
            f"/api/v1/students/me/goals/{goal.id}",
            headers=student_headers,
        )
        assert response.status_code == 204

        # Verify status changed
        await db_session.refresh(goal)
        assert goal.status == "abandoned"


class TestAdminFacultyReadAccess:
    """Admin/faculty can view any student's profile and goals."""

    @pytest.mark.asyncio
    async def test_admin_can_read_student_profile(self, client, admin_headers, db_session, test_student):
        """GET /students/{id}/profile works for admin."""
        db_session.add(StudentProfile(
            id=uuid.uuid4(), user_id=test_student.id,
            interests=["ai"], strengths=["coding"],
            career_goals=["researcher"], daily_study_hours_target=4,
        ))
        await db_session.flush()

        response = await client.get(
            f"/api/v1/students/{test_student.id}/profile",
            headers=admin_headers,
        )
        assert response.status_code == 200
        assert response.json()["interests"] == ["ai"]

    @pytest.mark.asyncio
    async def test_faculty_can_read_student_goals(self, client, faculty_headers, db_session, test_student):
        """GET /students/{id}/goals works for faculty."""
        db_session.add(StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Faculty-visible goal", category="skill", status="active", priority="high",
        ))
        await db_session.flush()

        response = await client.get(
            f"/api/v1/students/{test_student.id}/goals",
            headers=faculty_headers,
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1