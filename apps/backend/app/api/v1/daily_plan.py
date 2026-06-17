"""
Daily Plan API — Free Periods + Daily Routine endpoints.
All under /api/v1/students prefix, registered in main.py.
"""

import uuid
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.course import Enrollment, Course
from app.models.session import TimetableSlot
from app.models.student_goal import StudentGoal
from app.models.student_profile import StudentProfile
from app.models.user import User
from app.services.daily_routine_service import (
    DailyRoutineService,
    invalidate_routine_cache,
)
from app.services.free_period_service import FreePeriodService
from app.services.llm_client import LLMClient
from app.services.task_suggestion_service import TaskSuggestionService

router = APIRouter()

# Singleton LLM client (reused across requests)
_llm_client: LLMClient | None = None


def _get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _get_student_enrollments(db: AsyncSession, student_id: UUID) -> list[dict]:
    """Return enrolled courses as list of dicts."""
    result = await db.execute(
        select(Enrollment.course_id)
        .where(Enrollment.student_id == student_id)
    )
    course_ids = [r for r in result.scalars().all()]
    if not course_ids:
        return []
    courses_result = await db.execute(
        select(Course).where(Course.id.in_(course_ids))
    )
    return [
        {"id": str(c.id), "name": c.name, "code": c.code}
        for c in courses_result.scalars().all()
    ]


async def _get_student_profile_and_goals(
    db: AsyncSession, student_id: UUID
) -> tuple[StudentProfile | None, list[StudentGoal]]:
    """Fetch profile and active goals for a student."""
    profile_result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == student_id)
    )
    profile = profile_result.scalar_one_or_none()

    goals_result = await db.execute(
        select(StudentGoal)
        .where(
            StudentGoal.student_id == student_id,
            StudentGoal.status == "active",
        )
        .order_by(
            StudentGoal.priority.desc(),
            StudentGoal.target_date.asc().nullslast(),
        )
    )
    goals = list(goals_result.scalars().all())
    return profile, goals


# ─── Free Period Endpoints ────────────────────────────────────────────────────


@router.get("/me/free-periods")
async def get_free_periods(
    target_date: date = Query(default=None),  # defaults to today
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return free periods for a given date with task suggestions.
    If target_date is omitted, uses today's date.
    """
    if target_date is None:
        target_date = date.today()

    fp_svc = FreePeriodService(db)
    free_periods = await fp_svc.detect_free_periods(current_user.id, target_date)

    profile, goals = await _get_student_profile_and_goals(db, current_user.id)
    enrolled_courses = await _get_student_enrollments(db, current_user.id)

    # Get today's classes
    weekday = target_date.weekday()
    result = await db.execute(
        select(TimetableSlot, Course)
        .join(Course, TimetableSlot.course_id == Course.id)
        .where(
            TimetableSlot.course_id.in_([c["id"] for c in enrolled_courses])
            if enrolled_courses else False,
            TimetableSlot.day_of_week == weekday,
        )
        .order_by(TimetableSlot.start_time)
    )
    slots_with_course = list(result.all())
    classes = [
        {
            "course_name": course.name,
            "start_time": slot.start_time.strftime("%H:%M"),
            "end_time": slot.end_time.strftime("%H:%M"),
            "room": slot.room,
        }
        for slot, course in slots_with_course
    ]

    # Attach suggestions to each free period
    llm = _get_llm_client()
    suggestion_svc = TaskSuggestionService(llm, db)

    enriched_free_periods = []
    for fp in free_periods:
        suggestions = await suggestion_svc.suggest_tasks(
            student_id=current_user.id,
            free_period=fp,
            profile=profile,
            active_goals=goals,
            enrolled_courses=enrolled_courses,
            target_date=target_date,
        )
        # Resolve goal IDs — map index to real UUID
        goal_map = {str(i): g.id for i, g in enumerate(goals)}
        for s in suggestions:
            if s.get("goal_id") in goal_map:
                s["goal_id"] = str(goal_map[s["goal_id"]])

        enriched_free_periods.append({
            **fp,
            "suggestions": suggestions,
        })

    return {
        "date": target_date.isoformat(),
        "classes": classes,
        "free_periods": enriched_free_periods,
        "profile_incomplete": profile is None,
    }


@router.get("/me/free-periods/week")
async def get_free_periods_week(
    week_start: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return free periods for Mon-Fri starting from week_start."""
    fp_svc = FreePeriodService(db)
    profile, goals = await _get_student_profile_and_goals(db, current_user.id)
    enrolled_courses = await _get_student_enrollments(db, current_user.id)

    llm = _get_llm_client()
    suggestion_svc = TaskSuggestionService(llm, db)

    result = {}
    current = week_start
    for _ in range(5):
        free_periods = await fp_svc.detect_free_periods(current_user.id, current)
        enriched = []
        for fp in free_periods:
            suggestions = await suggestion_svc.suggest_tasks(
                current_user.id, fp, profile, goals, enrolled_courses, current
            )
            # Resolve goal IDs
            goal_map = {str(i): g.id for i, g in enumerate(goals)}
            for s in suggestions:
                if s.get("goal_id") in goal_map:
                    s["goal_id"] = str(goal_map[s["goal_id"]])
            enriched.append({**fp, "suggestions": suggestions})
        result[current.isoformat()] = {
            "free_periods": enriched,
            "profile_incomplete": profile is None,
        }
        current += timedelta(days=1)

    return result


# ─── Daily Routine Endpoints ──────────────────────────────────────────────────


@router.get("/me/routine")
async def get_daily_routine(
    target_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate and return the full daily routine for a student.
    Caches result in Redis (4h TTL).
    """
    if target_date is None:
        target_date = date.today()

    llm = _get_llm_client()
    svc = DailyRoutineService(llm, db)
    return await svc.generate_daily_routine(current_user.id, target_date)


@router.get("/me/routine/weekly")
async def get_weekly_routine(
    week_start: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return routines for Mon-Fri starting from week_start."""
    llm = _get_llm_client()
    svc = DailyRoutineService(llm, db)

    result = {}
    current = week_start
    for _ in range(5):
        result[current.isoformat()] = await svc.generate_daily_routine(
            current_user.id, current
        )
        current += timedelta(days=1)
    return result


# ─── Cache Invalidation Webhook ───────────────────────────────────────────────


@router.post("/me/routine/invalidate")
async def invalidate_routine(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invalidate cached routine for the current user. Called after profile/goal updates."""
    await invalidate_routine_cache(current_user.id)
    return {"status": "ok"}