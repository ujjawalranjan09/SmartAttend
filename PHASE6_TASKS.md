# Phase 6 Implementation Task Tracker

> Updated after each task completion.

## Status Legend
- ✅ = done
- 🔄 = in progress
- ⬜ = pending

## Tasks

| # | Task | Status | Notes |
|---|------|--------|-------|
| 1.1 | StudentProfile model + register in __init__.py | ✅ | |
| 1.2 | StudentGoal model + register in __init__.py | ✅ | |
| 1.3 | Pydantic schemas for profile & goals | ✅ | |
| 1.4 | Student Profile & Goals API endpoints | ✅ | |
| 1.5 | Tests for profile & goals API | ✅ | 15 tests, found and fixed milestone update bug (missing `flag_modified` for JSON list mutation) |
| 1.6 | Frontend: Profile page + API client | ✅ | Tag-input forms, goal cards with milestone toggling, progress logging, cache invalidation on profile/goal changes |
| 2.0 | Update config.py with OpenRouter/LLM settings | ✅ | `openrouter_api_key`, `openrouter_model`, `openrouter_base_url`, `llm_max_tokens` already in place |
| 2.1 | Create LLM client (llm_client.py) with OpenRouter | ✅ | httpx-based, retry with temp=0 on parse failure, LLMServiceError |
| 2.2 | Create FreePeriodService | ✅ | 8:00-18:00 campus day, strict >30min gap exclusion |
| 2.3 | Create TaskSuggestionService (LLM + Redis cache + fallback) | ✅ | Redis cache (4h TTL), rule-based fallback, goal linking by fuzzy match |
| 2.4 | Create daily_plan.py API (free periods + routine) | ✅ | GET /me/free-periods, /me/free-periods/week, /me/routine, /me/routine/weekly, /me/routine/invalidate |
| 2.5 | Write tests for free periods (mock LLM + Redis) | ✅ | 8 tests: gap detection, LLM suggestions, fallback, cache, no-profile case |
| 2.6 | Frontend: Daily Plan view + API client | ✅ | Free periods tab with suggestion cards, Routine tab with timeline blocks |
| 3.1 | Create DailyRoutineService (LLM + cache + fallback) | ✅ | Redis cache (4h TTL), deterministic fallback, profile_incomplete flag, summary + daily_tip |
| 3.2 | Write tests for daily routine (mock LLM + cache invalidation) | ✅ | 6 tests: LLM routine, fallback, cache hit, cache invalidation, no-profile flag, daily_tip present |
| 3.3 | Frontend: Routine tab + dashboard card | ✅ | Routine timeline with color-coded blocks, summary card, regenerate button, Today's Routine on student dashboard |
| 4.1 | Display token API + endpoints | ✅ | JWT scoped token (4h expiry), /sessions/{id}/display-token, /display/session/{id} |
| 4.2 | Classroom Display HTML page | ✅ | Dark full-screen, live counter ring, sliding student list, WebSocket real-time updates, auto-reconnect |
| 4.3 | Frontend: Display buttons in sessions + live-session | ✅ | "Display" button in session cards, "Projector Mode" in live-session view, copy/open modal |
| 4.4 | Verify WebSocket broadcast payload | ✅ | Payload confirmed: student_name, roll_number, marked_at, status, present_count, total_enrolled |
| 99 | Run migrations (006, 007) + full test suite | ✅ | 118/118 tests pass. Stamped DB to 007 (already had tables). Fixed: displayApi URL, MIN_GAP threshold (>= to >), cache profile_incomplete injection, fallback test missing TimetableSlot |

---

## Changelog

<!--
2026-06-17 16:40 - All tasks pending, plan loaded.
2026-06-17 16:50 - Tasks 1.1-1.4 completed (models, schemas, API, registrations).
                   Updated task list to reflect latest plan (LLM client, Redis caching, daily_plan.py split).
2026-06-17 18:55 - Task 1.5 completed. 15/15 tests pass. Fixed bug: `update_goal_progress`
                   didn't persist JSON milestone mutations — added `flag_modified(goal, "milestones")`.
2026-06-17 19:15 - ALL PHASE 6 TASKS COMPLETE. 118/118 tests pass.
                   Fixes applied: displayApi URL (was /display/sessions/, correct /sessions/),
                   free_period MIN_GAP threshold (> instead of >= to exclude exactly-30-min gaps),
                   daily_routine cache missing profile_incomplete (inject on cache hit + before caching),
                   test_two_classes test missing pre-class free period assertion,
                   test_fallback test missing TimetableSlot (added),
                   classroom-display.html moved to frontend root for correct URL path,
                   DB stamped to 007 (tables already existed).
-->