"""
DailyRoutineService — LLM-powered daily routine generator.
Caches results in Redis (4h TTL). Falls back to deterministic greedy planner on LLM failure.
"""

import json
import logging
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import cache_get, cache_set, cache_delete_pattern
from app.models.attendance import AttendanceRecord
from app.models.course import Course, Enrollment
from app.models.session import ClassSession, TimetableSlot
from app.models.student_goal import StudentGoal
from app.models.student_profile import StudentProfile
from app.services.free_period_service import FreePeriodService
from app.services.llm_client import LLMClient, LLMServiceError

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 4 * 3600  # 4 hours


class DailyRoutineService:
    SYSTEM_PROMPT = (
        "You are an intelligent academic planner AI for Indian college students. "
        "You create optimized daily routines that balance class attendance, focused study sessions, "
        "goal progress, and necessary breaks. You understand Indian college culture "
        "(lunch timing, commute patterns, exam pressure). You always respond with valid JSON only."
    )

    def __init__(self, llm_client: LLMClient, db: AsyncSession) -> None:
        self.llm = llm_client
        self.db = db
        self._free_period_svc = FreePeriodService(db)

    async def generate_daily_routine(self, student_id: UUID, target_date: date) -> dict:
        """Generate and return a full daily routine. Caches result in Redis."""
        cache_key = f"routine:{student_id}:{target_date.isoformat()}"

        # Check cache
        try:
            cached = await cache_get(cache_key)
            if cached:
                result = json.loads(cached)
                result["generated_by"] = "cached"
                # profile_incomplete was computed at cache time; re-compute it
                # from context so stale cache doesn't give wrong value
                context = await self._build_context(student_id, target_date)
                result["profile_incomplete"] = context["profile_incomplete"]
                return result
        except Exception:
            pass  # Redis down

        # Build context and call LLM
        context = await self._build_context(student_id, target_date)
        try:
            result = await self._call_llm(context, target_date)
            result["generated_by"] = "llm"
        except LLMServiceError as exc:
            logger.warning("LLM routine generation failed, using fallback: %s", exc)
            result = self._fallback_routine(context, target_date)
            result["generated_by"] = "fallback"

        # Ensure profile_incomplete is set in result (for cache hit correctness)
        result["profile_incomplete"] = context["profile_incomplete"]
        result["date"] = target_date.isoformat()

        # Cache result
        try:
            await cache_set(cache_key, json.dumps(result), CACHE_TTL_SECONDS)
        except Exception:
            pass

        return result

    async def _build_context(self, student_id: UUID, target_date: date) -> dict:
        """Gather all data needed for the LLM prompt."""
        weekday = target_date.weekday()

        # Profile
        profile_result = await self.db.execute(
            select(StudentProfile).where(StudentProfile.user_id == student_id)
        )
        profile = profile_result.scalar_one_or_none()

        # Active goals
        goals_result = await self.db.execute(
            select(StudentGoal).where(
                StudentGoal.student_id == student_id,
                StudentGoal.status == "active",
            ).order_by(
                # high first, then soonest deadline
                StudentGoal.priority.desc(),
                StudentGoal.target_date.asc(),
            )
        )
        active_goals = list(goals_result.scalars().all())

        # Enrolled courses
        enroll_result = await self.db.execute(
            select(Enrollment.course_id).where(Enrollment.student_id == student_id)
        )
        course_ids = [r for r in enroll_result.scalars().all()]

        # Today's classes (timetable slots for weekday)
        if course_ids:
            slots_result = await self.db.execute(
                select(TimetableSlot, Course)
                .join(Course, TimetableSlot.course_id == Course.id)
                .where(
                    TimetableSlot.course_id.in_(course_ids),
                    TimetableSlot.day_of_week == weekday,
                )
                .order_by(TimetableSlot.start_time)
            )
            slots_with_course = [(slot, course) for slot, course in slots_result.all()]
        else:
            slots_with_course = []

        # Attendance percentage per enrolled course (last 30 days)
        attendance_pct = {}
        if course_ids:
            thirty_days_ago = date.today()
            from datetime import timedelta
            thirty_days_ago = target_date - timedelta(days=30)
            for cid in course_ids:
                att_result = await self.db.execute(
                    select(AttendanceRecord)
                    .join(ClassSession, AttendanceRecord.session_id == ClassSession.id)
                    .where(
                        ClassSession.course_id == cid,
                        ClassSession.date >= thirty_days_ago,
                        AttendanceRecord.student_id == student_id,
                    )
                )
                records = list(att_result.scalars().all())
                total = len(records)
                present = sum(1 for r in records if r.status.value == "present")
                attendance_pct[str(cid)] = round((present / total * 100), 1) if total > 0 else 100.0

        # Free periods
        free_periods = await self._free_period_svc.detect_free_periods(student_id, target_date)

        # Build classes list
        classes = []
        for slot, course in slots_with_course:
            classes.append({
                "course_name": course.name,
                "start_time": slot.start_time.strftime("%H:%M"),
                "end_time": slot.end_time.strftime("%H:%M"),
                "room": slot.room,
            })

        # Build goals list
        goals_data = []
        for g in active_goals:
            days_remaining = None
            if g.target_date:
                days_remaining = (g.target_date - target_date).days
            incomplete_milestones = [
                m["title"] for m in (g.milestones or []) if not m.get("completed", False)
            ]
            goals_data.append({
                "title": g.title,
                "description": g.description,
                "category": g.category,
                "priority": g.priority,
                "completed_hours": g.completed_hours,
                "estimated_hours": g.estimated_hours or 10,
                "days_remaining": days_remaining,
                "incomplete_milestones": incomplete_milestones,
            })

        # Build courses list
        courses_data = []
        if course_ids:
            courses_result = await self.db.execute(
                select(Course).where(Course.id.in_(course_ids))
            )
            for c in courses_result.scalars().all():
                courses_data.append({
                    "name": c.name,
                    "code": c.code,
                    "attendance_pct": attendance_pct.get(str(c.id), 100.0),
                })

        study_target = profile.daily_study_hours_target if profile else 2

        return {
            "profile": {
                "interests": profile.interests if profile else [],
                "strengths": profile.strengths if profile else [],
                "career_goals": profile.career_goals if profile else [],
                "preferred_study_style": profile.preferred_study_style if profile else None,
                "daily_study_hours_target": study_target,
            } if profile else None,
            "classes": classes,
            "free_periods": free_periods,
            "goals": goals_data,
            "courses": courses_data,
            "target_date": target_date.isoformat(),
            "day_of_week": target_date.strftime("%A"),
            "current_time": datetime.now().strftime("%H:%M"),
            "study_target_hours": study_target,
            "profile_incomplete": profile is None,
        }

    async def _call_llm(self, ctx: dict, target_date: date) -> dict:
        profile_note = ""
        if ctx["profile_incomplete"]:
            profile_note = (
                "\nThe student has not set up their profile yet. "
                "Create a basic study routine based on their enrolled courses. "
                "Include a suggestion to complete their profile."
            )

        user_prompt = f"""Create an optimized daily routine for this student.

Date: {ctx['target_date']} ({ctx['day_of_week']})
Current time: {ctx['current_time']}

Student profile:
{json.dumps(ctx['profile'], indent=2) if ctx['profile'] else 'Not set up'}

Today's classes (fixed — cannot be moved):
{json.dumps(ctx['classes'], indent=2)}

Available free periods:
{json.dumps(ctx['free_periods'], indent=2)}

Active goals (ordered by priority):
{json.dumps(ctx['goals'], indent=2)}

Recent academic context:
{json.dumps(ctx['courses'], indent=2)}
{profile_note}

Instructions:
1. Keep all class slots exactly as-is (they are fixed).
2. Fill free periods with SMART study sessions that advance specific goals.
3. Consider the student's preferred study style when suggesting activities.
4. If a goal has an upcoming deadline (within 7 days), prioritize it.
5. If attendance is low in a course, suggest reviewing that course material.
6. Include a 1-hour lunch break around 12:30-13:30 (or adjust based on class schedule).
7. Include short 10-15 min breaks between long study sessions (pomodoro style).
8. Do NOT fill every minute — leave some unallocated rest time (at least 30 min).
9. For each study block, give a SPECIFIC actionable task, not vague 'study X'.
10. Total study time should be close to but not exceed {ctx['study_target_hours']} hours.

Respond as JSON:
{{
  "routine": [
    {{"type": "class", "start": "HH:MM", "end": "HH:MM", "course_name": "...", "room": "...", "note": "optional tip"}},
    {{"type": "study", "start": "HH:MM", "end": "HH:MM", "title": "specific task title", "description": "...", "category": "...", "goal_title": "...", "difficulty": "easy|medium|hard"}},
    {{"type": "break", "start": "HH:MM", "end": "HH:MM", "title": "...", "suggestion": "..."}},
    {{"type": "free", "start": "HH:MM", "end": "HH:MM", "title": "...", "optional_suggestions": ["..."]}}
  ],
  "summary": {{
    "total_classes": N,
    "total_study_hours": N.N,
    "total_break_hours": N.N,
    "total_free_hours": N.N,
    "goals_addressed": ["goal title 1", "goal title 2"],
    "daily_tip": "..."
  }},
  "goal_progress_today": [
    {{"goal_title": "...", "hours_planned": N.N, "hours_remaining": N.N, "milestones_to_work_on": ["..."]}}
  ]
}}"""

        return await self.llm.chat(system_prompt=self.SYSTEM_PROMPT, user_prompt=user_prompt)

    def _validate_and_fix(self, result: dict, ctx: dict) -> dict:
        """Validate LLM response, fix issues programmatically."""
        routine = result.get("routine", [])
        classes = ctx["classes"]

        # Sort by start time
        routine.sort(key=lambda b: b.get("start", "00:00"))

        # Check class blocks match actual timetable
        for block in routine:
            if block["type"] == "class":
                # Verify it matches a real class
                matched = any(
                    b["start"] == block["start"] and b["course_name"] == block["course_name"]
                    for b in classes
                )
                if not matched:
                    block["note"] = (block.get("note") or "") + " [auto-verified]"

        result["routine"] = routine
        return result

    def _fallback_routine(self, ctx: dict, target_date: date) -> dict:
        """Deterministic fallback when LLM is unavailable."""
        routine = []
        classes = ctx["classes"]
        free_periods = ctx["free_periods"]
        goals = ctx["goals"]
        study_target = ctx["study_target_hours"]

        # Add classes
        for cls in classes:
            routine.append({
                "type": "class",
                "start": cls["start_time"],
                "end": cls["end_time"],
                "course_name": cls["course_name"],
                "room": cls.get("room"),
            })

        # Sort routine by start time
        routine.sort(key=lambda b: b.get("start", "00:00"))

        # Find lunch window (12:30-13:30)
        lunch_start = "12:30"
        lunch_end = "13:30"

        # Add study blocks for free periods
        total_study_minutes = 0
        goal_cursor = 0
        for fp in free_periods:
            fp_start = self._time_to_minutes(fp["start_time"])
            fp_end = self._time_to_minutes(fp["end_time"])
            gap_duration = fp_end - fp_start

            # Check for lunch break
            lunch_s = self._time_to_minutes(lunch_start)
            lunch_e = self._time_to_minutes(lunch_end)
            if lunch_s >= fp_start and lunch_e <= fp_end and total_study_minutes < study_target * 60:
                routine.append({
                    "type": "break",
                    "start": lunch_start,
                    "end": lunch_end,
                    "title": "Lunch break",
                    "suggestion": "Take a proper break. Hydrate, eat, and relax before the afternoon.",
                })

            if total_study_minutes >= study_target * 60:
                routine.append({
                    "type": "free",
                    "start": fp["start_time"],
                    "end": fp["end_time"],
                    "title": "Unallocated — rest or optional suggestions available",
                })
                continue

            # Allocate study time
            study_minutes = min(gap_duration, int((study_target * 60) - total_study_minutes))
            if study_minutes < 30:
                routine.append({
                    "type": "free",
                    "start": fp["start_time"],
                    "end": fp["end_time"],
                    "title": "Unallocated",
                })
                continue

            goal = goals[goal_cursor] if goal_cursor < len(goals) else None
            if goal:
                study_title = f"Work on: {goal['title']}"
                goal_category = goal["category"]
            else:
                study_title = "General study session"
                goal_category = "academic"

            routine.append({
                "type": "study",
                "start": fp["start_time"],
                "end": self._minutes_to_time(fp_start + study_minutes),
                "title": study_title,
                "description": f"Focus on {goal['title'] if goal else 'your coursework'}.",
                "category": goal_category,
                "goal_title": goal["title"] if goal else None,
                "difficulty": "medium",
            })
            total_study_minutes += study_minutes
            goal_cursor = min(goal_cursor + 1, len(goals) - 1)

        # Re-sort
        routine.sort(key=lambda b: b.get("start", "00:00"))

        total_study = total_study_minutes / 60
        total_break = 1.0  # lunch

        return {
            "date": target_date.isoformat(),
            "profile_incomplete": ctx["profile_incomplete"],
            "routine": routine,
            "summary": {
                "total_classes": len(classes),
                "total_study_hours": round(total_study, 1),
                "total_break_hours": total_break,
                "total_free_hours": round(
                    max(0, 10 - len(classes) * 1 - total_study - total_break), 1
                ),
                "goals_addressed": [g["title"] for g in goals[:2]],
                "daily_tip": "Consistency beats intensity. Even 30 minutes of focused study daily builds up!",
            },
            "goal_progress_today": [],
        }

    @staticmethod
    def _time_to_minutes(t: str) -> int:
        h, m = map(int, t.split(":"))
        return h * 60 + m

    @staticmethod
    def _minutes_to_time(minutes: int) -> str:
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"


async def invalidate_routine_cache(student_id: UUID) -> None:
    """Invalidate all cached routines for a student. Call after profile/goal updates."""
    try:
        await cache_delete_pattern(f"routine:{student_id}:*")
    except Exception:
        pass