"""
TaskSuggestionService — LLM-powered study task suggestions for free periods.
Falls back to rule-based suggestions if the LLM is unavailable.
Caches results in Redis (4h TTL).
"""

import json
import logging
from datetime import date
from difflib import SequenceMatcher
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import cache_get, cache_set
from app.models.student_goal import StudentGoal
from app.models.student_profile import StudentProfile
from app.services.free_period_service import FreePeriodService
from app.services.llm_client import LLMClient, LLMServiceError

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 4 * 3600  # 4 hours


class TaskSuggestionService:
    SYSTEM_PROMPT = (
        "You are an academic advisor AI for Indian college students. "
        "You suggest productive study tasks for free periods between classes. "
        "You consider the student's interests, strengths, career goals, active goals with deadlines, "
        "and the available time. Always respond with valid JSON only."
    )

    def __init__(self, llm_client: LLMClient, db: AsyncSession) -> None:
        self.llm = llm_client
        self.db = db
        self._free_period_svc = FreePeriodService(db)

    async def suggest_tasks(
        self,
        student_id: UUID,
        free_period: dict,
        profile: StudentProfile | None,
        active_goals: list[StudentGoal],
        enrolled_courses: list[dict],
        target_date: date,
    ) -> list[dict]:
        """
        Return 2-3 task suggestions for a free period.
        Uses LLM with Redis caching + rule-based fallback.
        """
        # Build cache key
        cache_key = (
            f"suggestions:{student_id}:{target_date.isoformat()}:"
            f"{free_period['start_time']}"
        )

        # Check cache
        try:
            cached = await cache_get(cache_key)
            if cached:
                logger.debug("Cache hit for suggestions: %s", cache_key)
                return json.loads(cached)
        except Exception:
            pass  # Redis down — proceed without cache

        # Build context
        context = self._build_context(
            profile, active_goals, enrolled_courses, free_period, target_date
        )

        try:
            suggestions = await self._call_llm(context, profile)
        except LLMServiceError as exc:
            logger.warning("LLM call failed, using fallback: %s", exc)
            suggestions = self._fallback_suggestions(free_period, active_goals, enrolled_courses)

        # Cache result
        try:
            await cache_set(cache_key, json.dumps(suggestions), CACHE_TTL_SECONDS)
        except Exception:
            pass  # Redis down — proceed without caching

        return suggestions

    def _build_context(
        self,
        profile: StudentProfile | None,
        active_goals: list[StudentGoal],
        enrolled_courses: list[dict],
        free_period: dict,
        target_date: date,
    ) -> dict:
        goals_data = []
        for g in active_goals:
            days_remaining = None
            if g.target_date:
                days_remaining = (g.target_date - target_date).days
            incomplete_milestones = [
                m for m in (g.milestones or []) if not m.get("completed", False)
            ]
            goals_data.append({
                "title": g.title,
                "category": g.category,
                "priority": g.priority,
                "completed_hours": g.completed_hours,
                "estimated_hours": g.estimated_hours,
                "incomplete_milestones": [m["title"] for m in incomplete_milestones],
                "target_date": str(g.target_date) if g.target_date else None,
                "days_remaining": days_remaining,
            })

        if profile:
            profile_data = {
                "interests": profile.interests or [],
                "strengths": profile.strengths or [],
                "career_goals": profile.career_goals or [],
                "preferred_study_style": profile.preferred_study_style,
                "daily_study_hours_target": profile.daily_study_hours_target,
            }
        else:
            profile_data = None

        return {
            "profile": profile_data,
            "goals": goals_data,
            "courses": enrolled_courses,
            "free_period": free_period,
            "date": target_date.isoformat(),
            "day_of_week": target_date.strftime("%A"),
            "profile_incomplete": profile is None,
        }

    async def _call_llm(self, context: dict, profile: StudentProfile | None) -> list[dict]:
        user_prompt_parts = []

        if profile:
            user_prompt_parts.append(f"Student profile: {json.dumps(context['profile'], indent=2)}")
        else:
            user_prompt_parts.append(
                "The student has not completed their profile yet. "
                "Suggest general productive study tasks based on their enrolled courses."
            )

        user_prompt_parts.extend([
            f"Active goals: {json.dumps(context['goals'], indent=2)}",
            f"Enrolled courses: {json.dumps(context['courses'], indent=2)}",
            f"Free period: {json.dumps(context['free_period'], indent=2)}",
            "",
            "Suggest 2-3 specific, actionable tasks the student should do during this free period. "
            "For each suggestion, provide:\n"
            "- title: short actionable title\n"
            "- description: 2-3 sentence specific instruction\n"
            "- category: one of [academic, career, skill, project, exam_prep, general]\n"
            "- duration_minutes: must fit within the free period\n"
            "- linked_goal_title: which active goal this advances (or null if general)\n"
            "- priority_score: 0.0-1.0 how strongly you recommend this\n"
            "- reasoning: one sentence explaining why this task fits this student\n"
            '\nRespond as JSON: {"suggestions": [{...}, ...]}',
        ])

        response = await self.llm.chat(
            system_prompt=self.SYSTEM_PROMPT,
            user_prompt="\n\n".join(user_prompt_parts),
        )

        suggestions = response.get("suggestions", [])

        # Resolve goal IDs
        for s in suggestions:
            s["goal_id"] = self._resolve_goal_id(
                s.get("linked_goal_title"), context["goals"]
            )
            if s.get("linked_goal_title"):
                del s["linked_goal_title"]
            if "reasoning" in s:
                del s["reasoning"]  # internal-use only

        # Sort by priority_score descending
        suggestions.sort(key=lambda x: x.get("priority_score", 0), reverse=True)
        return suggestions[:3]

    def _resolve_goal_id(self, linked_title: str | None, goals: list[dict]) -> str | None:
        if not linked_title:
            return None
        best_score = 0
        best_id = None
        for i, g in enumerate(goals):
            score = SequenceMatcher(None, linked_title.lower(), g["title"].lower()).ratio()
            if score > best_score and score > 0.5:
                best_score = score
                best_id = str(i)  # We'll map back to real IDs in the API layer
        return best_id

    def _fallback_suggestions(
        self,
        free_period: dict,
        active_goals: list[StudentGoal],
        enrolled_courses: list[dict],
    ) -> list[dict]:
        """Rule-based fallback when LLM is unavailable."""
        duration = free_period["duration_minutes"]

        # Pick highest-priority active goal
        priority_order = {"high": 0, "medium": 1, "low": 2}
        sorted_goals = sorted(
            active_goals, key=lambda g: priority_order.get(g.priority, 1)
        )
        top_goal = sorted_goals[0] if sorted_goals else None

        course_name = enrolled_courses[0]["name"] if enrolled_courses else "your courses"

        if duration <= 45:
            suggestions = [
                {
                    "title": f"Review notes for {course_name}",
                    "description": f"Quickly review lecture notes or slides from your recent {course_name} class to reinforce key concepts.",
                    "category": "academic",
                    "duration_minutes": min(duration, 30),
                    "goal_id": str(top_goal.id) if top_goal else None,
                    "priority_score": 0.7,
                }
            ]
        elif duration <= 90:
            suggestions = [
                {
                    "title": f"Work on {top_goal.title}" if top_goal else f"Practice problems for {course_name}",
                    "description": (
                        f"{'Work through the next milestone of your goal: ' + top_goal.title + '. ' if top_goal else ''}"
                        "Solve 3-5 practice problems or review a chapter section."
                    ),
                    "category": top_goal.category if top_goal else "academic",
                    "duration_minutes": min(duration, 60),
                    "goal_id": str(top_goal.id) if top_goal else None,
                    "priority_score": 0.8,
                }
            ]
        else:
            suggestions = [
                {
                    "title": f"Deep work on {top_goal.title}" if top_goal else f"Deep study session — {course_name}",
                    "description": (
                        f"{'Focus on implementing or studying the core concepts of your goal: ' + top_goal.title + '. ' if top_goal else ''}"
                        "Set a timer for 50 minutes and do focused work with no distractions."
                    ),
                    "category": top_goal.category if top_goal else "academic",
                    "duration_minutes": min(duration, 90),
                    "goal_id": str(top_goal.id) if top_goal else None,
                    "priority_score": 0.9,
                }
            ]
        return suggestions