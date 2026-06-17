"""Tests for Daily Routine Generator (Phase 6 Feature 3)."""
import uuid
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio

from app.models.course import Course, Enrollment
from app.models.student_goal import StudentGoal
from app.models.student_profile import StudentProfile
from app.services.daily_routine_service import DailyRoutineService, invalidate_routine_cache
from app.services.free_period_service import FreePeriodService
from app.services.llm_client import LLMClient, LLMServiceError


class TestDailyRoutineService:
    """Tests for DailyRoutineService with mocked LLM and Redis."""

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock(spec=LLMClient)
        llm.chat = AsyncMock(return_value={
            "routine": [
                {"type": "class", "start": "09:00", "end": "10:00",
                 "course_name": "Data Structures", "room": "301"},
                {"type": "study", "start": "10:00", "end": "11:30",
                 "title": "Practice tree traversals",
                 "description": "Implement inorder, preorder, postorder for BST.",
                 "category": "skill", "goal_title": "Master Algorithms",
                 "difficulty": "medium"},
                {"type": "break", "start": "11:30", "end": "12:30",
                 "title": "Lunch break"},
                {"type": "class", "start": "12:30", "end": "13:30",
                 "course_name": "OS", "room": "205"},
                {"type": "free", "start": "13:30", "end": "18:00",
                 "title": "Rest / personal time"},
            ],
            "summary": {
                "total_classes": 2,
                "total_study_hours": 1.5,
                "total_break_hours": 1.0,
                "total_free_hours": 4.5,
                "goals_addressed": ["Master Algorithms"],
                "daily_tip": "Small consistent efforts beat last-minute cramming!",
            },
            "goal_progress_today": [
                {"goal_title": "Master Algorithms", "hours_planned": 1.5,
                 "hours_remaining": 8.5, "milestones_to_work_on": ["Binary trees"]},
            ],
            "profile_incomplete": False,
        })
        return llm

    @pytest.mark.asyncio
    async def test_routine_includes_classes_in_order(
        self, db_session, test_student, test_institution, mock_llm
    ):
        """Generated routine includes all classes in chronological order."""
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Data Structures", code="CS201",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        await db_session.flush()

        # Add profile so LLM is called
        db_session.add(StudentProfile(
            id=uuid.uuid4(), user_id=test_student.id,
            interests=["coding"], strengths=["problem solving"],
            career_goals=["software engineer"],
            preferred_study_style="hands-on",
            daily_study_hours_target=3,
        ))
        await db_session.flush()

        with patch("app.services.daily_routine_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.daily_routine_service.cache_set", new_callable=AsyncMock):

            svc = DailyRoutineService(mock_llm, db_session)
            result = await svc.generate_daily_routine(test_student.id, date.today())

        assert result["generated_by"] == "llm"
        routine = result["routine"]
        class_blocks = [b for b in routine if b["type"] == "class"]
        assert len(class_blocks) == 2
        assert class_blocks[0]["course_name"] == "Data Structures"

    @pytest.mark.asyncio
    async def test_fallback_generates_valid_routine(
        self, db_session, test_student, test_institution
    ):
        """When LLM fails, deterministic fallback produces a valid routine."""
        from datetime import time
        from app.models.session import TimetableSlot
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Mathematics", code="MA101",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        db_session.add(StudentProfile(
            id=uuid.uuid4(), user_id=test_student.id,
            interests=["math"], strengths=["analysis"],
            career_goals=["researcher"], daily_study_hours_target=2,
        ))
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Complete Math Problem Set", category="academic",
            priority="high", status="active", estimated_hours=10,
        )
        db_session.add(goal)
        # Add a timetable slot so the fallback has a class to include
        db_session.add(TimetableSlot(
            id=uuid.uuid4(), course_id=course.id,
            day_of_week=date.today().weekday(),
            start_time=time(9, 0), end_time=time(10, 0),
        ))
        await db_session.flush()

        # LLM raises error
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat = AsyncMock(side_effect=LLMServiceError("API down"))

        with patch("app.services.daily_routine_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.daily_routine_service.cache_set", new_callable=AsyncMock):

            svc = DailyRoutineService(mock_llm, db_session)
            result = await svc.generate_daily_routine(test_student.id, date.today())

        assert result["generated_by"] == "fallback"
        routine = result["routine"]
        # Should have at least class + study blocks
        assert any(b["type"] == "class" for b in routine)
        assert any(b["type"] == "study" for b in routine)

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_result(
        self, db_session, test_student, test_institution, mock_llm
    ):
        """Second call for same student+date returns cached result."""
        cached_result = {
            "date": date.today().isoformat(),
            "generated_by": "cached",
            "routine": [
                {"type": "class", "start": "09:00", "end": "10:00",
                 "course_name": "Cached Course", "room": "101"},
            ],
            "summary": {
                "total_classes": 1, "total_study_hours": 0.0,
                "total_break_hours": 0.0, "total_free_hours": 9.0,
                "goals_addressed": [],
                "daily_tip": "Cached tip.",
            },
            "goal_progress_today": [],
        }
        import json
        with patch("app.services.daily_routine_service.cache_get",
                   new_callable=AsyncMock,
                   return_value=json.dumps(cached_result)):

            svc = DailyRoutineService(mock_llm, db_session)
            result = await svc.generate_daily_routine(test_student.id, date.today())

        mock_llm.chat.assert_not_called()
        assert result["generated_by"] == "cached"

    @pytest.mark.asyncio
    async def test_cache_invalidation_clears_pattern(
        self, db_session, test_student
    ):
        """invalidate_routine_cache calls cache_delete_pattern with correct key."""
        with patch("app.services.daily_routine_service.cache_delete_pattern",
                   new_callable=AsyncMock) as mock_del:
            await invalidate_routine_cache(test_student.id)
            mock_del.assert_called_once_with(f"routine:{test_student.id}:*")

    @pytest.mark.asyncio
    async def test_no_profile_gets_profile_incomplete_flag(
        self, db_session, test_student, test_institution, mock_llm
    ):
        """Student without profile gets profile_incomplete: true in response."""
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Chemistry", code="CH101",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        await db_session.flush()
        # No profile added

        with patch("app.services.daily_routine_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.daily_routine_service.cache_set", new_callable=AsyncMock):

            svc = DailyRoutineService(mock_llm, db_session)
            result = await svc.generate_daily_routine(test_student.id, date.today())

        assert result["profile_incomplete"] is True

    @pytest.mark.asyncio
    async def test_daily_tip_and_summary_present(
        self, db_session, test_student, test_institution, mock_llm
    ):
        """LLM response includes daily_tip and summary fields."""
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Physics", code="PH101",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        db_session.add(StudentProfile(
            id=uuid.uuid4(), user_id=test_student.id,
            interests=["physics"], strengths=["calculus"],
            career_goals=["physicist"], daily_study_hours_target=2,
        ))
        await db_session.flush()

        with patch("app.services.daily_routine_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.daily_routine_service.cache_set", new_callable=AsyncMock):

            svc = DailyRoutineService(mock_llm, db_session)
            result = await svc.generate_daily_routine(test_student.id, date.today())

        assert "summary" in result
        assert "daily_tip" in result["summary"]
        assert result["summary"]["daily_tip"] != ""
        assert "total_classes" in result["summary"]
        assert "goal_progress_today" in result