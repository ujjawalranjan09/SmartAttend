"""Tests for Free Period Detection and Task Suggestions (Phase 6 Feature 2)."""
import uuid
from datetime import date, time, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio

from app.models.course import Course, Enrollment
from app.models.session import TimetableSlot
from app.models.student_goal import StudentGoal
from app.models.student_profile import StudentProfile
from app.models.user import User, UserRole
from app.services.free_period_service import FreePeriodService
from app.services.task_suggestion_service import TaskSuggestionService
from app.services.llm_client import LLMClient, LLMServiceError


class TestFreePeriodDetection:
    """Unit tests for FreePeriodService.detect_free_periods."""

    @pytest.mark.asyncio
    async def test_gaps_excluded_under_30_minutes(self, db_session, test_student, test_institution):
        """Gaps shorter than 30 minutes are excluded from results."""
        # Create a course + enrollment
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Test Course", code="TC101",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))

        # Slots at 9:00-10:00 and 10:30-11:30 (gap of 30 min — excluded)
        db_session.add(TimetableSlot(
            id=uuid.uuid4(), course_id=course.id, day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        ))
        db_session.add(TimetableSlot(
            id=uuid.uuid4(), course_id=course.id, day_of_week=0,
            start_time=time(10, 30), end_time=time(11, 30),
        ))
        await db_session.flush()

        svc = FreePeriodService(db_session)
        # Use a Monday (weekday=0)
        monday = date.today() - timedelta(days=date.today().weekday())
        gaps = await svc.detect_free_periods(test_student.id, monday)

        # 08:00-09:00 = 60 min, 11:30-18:00 = 390 min. No 30-min gap.
        assert len(gaps) == 2
        durations = [g["duration_minutes"] for g in gaps]
        assert 60 in durations
        assert 390 in durations

    @pytest.mark.asyncio
    async def test_two_classes_produce_two_free_periods(self, db_session, test_student, test_institution):
        """Classes at 9-10 and 12-13 produce free periods: pre-class (08:00-09:00), between classes (10:00-12:00), and post-last (13:00-18:00)."""
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Data Structures", code="CS201",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))

        db_session.add(TimetableSlot(
            id=uuid.uuid4(), course_id=course.id, day_of_week=0,
            start_time=time(9, 0), end_time=time(10, 0),
        ))
        db_session.add(TimetableSlot(
            id=uuid.uuid4(), course_id=course.id, day_of_week=0,
            start_time=time(12, 0), end_time=time(13, 0),
        ))
        await db_session.flush()

        svc = FreePeriodService(db_session)
        monday = date.today() - timedelta(days=date.today().weekday())
        gaps = await svc.detect_free_periods(test_student.id, monday)

        # 3 free periods: pre-class (08:00-09:00), mid-gap (10:00-12:00), post-last (13:00-18:00)
        assert len(gaps) == 3
        # Pre-class free period
        assert gaps[0]["start_time"] == "08:00"
        assert gaps[0]["end_time"] == "09:00"
        assert gaps[0]["duration_minutes"] == 60
        # Mid-class gap
        assert gaps[1]["start_time"] == "10:00"
        assert gaps[1]["end_time"] == "12:00"
        assert gaps[1]["duration_minutes"] == 120
        # Post-last free period
        assert gaps[2]["start_time"] == "13:00"
        assert gaps[2]["duration_minutes"] == 300  # 13:00-18:00

    @pytest.mark.asyncio
    async def test_no_enrollments_returns_full_campus_day(self, db_session, test_student):
        """Student with no enrollments gets the full campus day as free."""
        svc = FreePeriodService(db_session)
        monday = date.today() - timedelta(days=date.today().weekday())
        gaps = await svc.detect_free_periods(test_student.id, monday)

        assert len(gaps) == 1
        assert gaps[0]["start_time"] == "08:00"
        assert gaps[0]["end_time"] == "18:00"
        assert gaps[0]["duration_minutes"] == 600

    @pytest.mark.asyncio
    async def test_get_free_periods_for_week_returns_5_days(self, db_session, test_student):
        """get_free_periods_for_week returns Mon-Fri keyed by date string."""
        svc = FreePeriodService(db_session)
        week_start = date.today() - timedelta(days=date.today().weekday())
        result = await svc.get_free_periods_for_week(test_student.id, week_start)

        assert len(result) == 5
        for key in result:
            assert len(key) == 10  # YYYY-MM-DD format


class TestTaskSuggestionService:
    """Tests for TaskSuggestionService with mocked LLM and Redis."""

    @pytest.mark.asyncio
    async def test_llm_suggestions_have_valid_priority_score(
        self, db_session, test_student, test_institution
    ):
        """LLM suggestions include priority_score in 0-1 range."""
        # Setup: student with profile + goal + enrollment
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Machine Learning", code="ML301",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        db_session.add(StudentProfile(
            id=uuid.uuid4(), user_id=test_student.id,
            interests=["ml", "data science"],
            strengths=["mathematics"],
            career_goals=["ml engineer"],
            preferred_study_style="hands-on",
            daily_study_hours_target=3,
        ))
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Complete ML Course", category="academic",
            priority="high", status="active",
        )
        db_session.add(goal)
        await db_session.flush()

        # Mock LLM response
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat = AsyncMock(return_value={
            "suggestions": [
                {
                    "title": "Practice neural networks",
                    "description": "Work through chapter 5 exercises on backpropagation.",
                    "category": "academic",
                    "duration_minutes": 90,
                    "linked_goal_title": "Complete ML Course",
                    "priority_score": 0.92,
                    "reasoning": "Matches student's ML interest and advances active goal.",
                }
            ]
        })

        # Mock Redis
        with patch("app.services.task_suggestion_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.task_suggestion_service.cache_set", new_callable=AsyncMock):

            svc = TaskSuggestionService(mock_llm, db_session)
            suggestions = await svc.suggest_tasks(
                student_id=test_student.id,
                free_period={"start_time": "10:00", "end_time": "11:30", "duration_minutes": 90},
                profile=await db_session.get(StudentProfile, test_student.id),
                active_goals=[goal],
                enrolled_courses=[{"id": str(course.id), "name": "Machine Learning", "code": "ML301"}],
                target_date=date.today(),
            )

        assert len(suggestions) == 1
        s = suggestions[0]
        assert 0.0 <= s["priority_score"] <= 1.0
        assert s["title"] == "Practice neural networks"
        assert s["goal_id"] is not None  # goal ID resolved

    @pytest.mark.asyncio
    async def test_fallback_when_llm_fails(self, db_session, test_student, test_institution):
        """When LLM raises LLMServiceError, fallback rule-based suggestions are returned."""
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Algorithms", code="AL202",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        goal = StudentGoal(
            id=uuid.uuid4(), student_id=test_student.id,
            title="Master Sorting Algorithms", category="skill",
            priority="high", status="active",
        )
        db_session.add(goal)
        await db_session.flush()

        # Mock LLM to raise error
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat = AsyncMock(side_effect=LLMServiceError("API down"))

        with patch("app.services.task_suggestion_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.task_suggestion_service.cache_set", new_callable=AsyncMock):

            svc = TaskSuggestionService(mock_llm, db_session)
            suggestions = await svc.suggest_tasks(
                student_id=test_student.id,
                free_period={"start_time": "14:00", "end_time": "15:30", "duration_minutes": 90},
                profile=None,
                active_goals=[goal],
                enrolled_courses=[{"id": str(course.id), "name": "Algorithms", "code": "AL202"}],
                target_date=date.today(),
            )

        assert len(suggestions) >= 1
        # Should fall back to medium gap rule (45-90 min)
        assert any("sorting" in s["title"].lower() or "algorithms" in s["title"].lower()
                   for s in suggestions)

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm_call(self, db_session, test_student):
        """When Redis returns cached suggestions, LLM is not called."""
        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat = AsyncMock()

        cached_suggestions = [
            {"title": "Cached task", "category": "general", "duration_minutes": 30,
             "goal_id": None, "priority_score": 0.8}
        ]

        with patch("app.services.task_suggestion_service.cache_get",
                   new_callable=AsyncMock, return_value='[{"title":"Cached task","category":"general","duration_minutes":30,"goal_id":null,"priority_score":0.8}]'):

            svc = TaskSuggestionService(mock_llm, db_session)
            result = await svc.suggest_tasks(
                student_id=test_student.id,
                free_period={"start_time": "10:00", "end_time": "10:30", "duration_minutes": 30},
                profile=None,
                active_goals=[],
                enrolled_courses=[],
                target_date=date.today(),
            )

        mock_llm.chat.assert_not_called()
        assert result[0]["title"] == "Cached task"

    @pytest.mark.asyncio
    async def test_no_profile_gets_generic_suggestions(self, db_session, test_student, test_institution):
        """Student without a profile still gets suggestions (generic)."""
        course = Course(
            id=uuid.uuid4(), institution_id=test_institution.id,
            department_id=uuid.uuid4(), faculty_id=test_student.id,
            name="Physics", code="PH101",
        )
        db_session.add(course)
        db_session.add(Enrollment(student_id=test_student.id, course_id=course.id))
        await db_session.flush()

        mock_llm = MagicMock(spec=LLMClient)
        mock_llm.chat = AsyncMock(return_value={
            "suggestions": [
                {"title": "Review physics notes", "category": "academic",
                 "duration_minutes": 30, "linked_goal_title": None,
                 "priority_score": 0.7, "reasoning": "General review."}
            ]
        })

        with patch("app.services.task_suggestion_service.cache_get", new_callable=AsyncMock, return_value=None), \
             patch("app.services.task_suggestion_service.cache_set", new_callable=AsyncMock):

            svc = TaskSuggestionService(mock_llm, db_session)
            suggestions = await svc.suggest_tasks(
                student_id=test_student.id,
                free_period={"start_time": "10:00", "end_time": "11:00", "duration_minutes": 60},
                profile=None,
                active_goals=[],
                enrolled_courses=[{"id": str(course.id), "name": "Physics", "code": "PH101"}],
                target_date=date.today(),
            )

        # LLM was called with reduced context
        mock_llm.chat.assert_called_once()
        call_args = mock_llm.chat.call_args
        assert "not completed their profile" in call_args[1]["user_prompt"]