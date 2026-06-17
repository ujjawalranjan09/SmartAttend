# Phase 6 Implementation Plan — Closing the Problem Statement Gaps

> **Goal:** Implement the 4 missing features from the problem statement's Expected Outcomes.
> **Prerequisite:** Phases 1-5 are complete (all existing backend/frontend/ML code is in place).
> **Convention:** Every task specifies the exact file to create or modify, what to build, and how to verify. No ambiguity.

---

## Overview — What's Missing

| # | Feature | Problem Statement Outcome |
|---|---------|--------------------------|
| 1 | Student Profile & Goals System | Foundation for #2 and #3 |
| 2 | Free Period Task Suggestions (LLM-powered) | "Suggests personalized academic tasks during free periods based on interests, strengths, and career goals" |
| 3 | Daily Routine Generator (LLM-powered) | "Generates a daily routine combining class schedule, free time, and long-term personal goals" |
| 4 | Classroom Display Screen | "Displays real-time attendance on a classroom screen" |

BLE/Wi-Fi proximity is deferred — QR + face recognition already satisfy the attendance method requirement. The DB schema already has `wifi_bssid` and `ble_beacon` columns ready for future use.

---

## Feature 1 — Student Profile & Goals

### 1.1 — StudentProfile Model

**Create file:** `apps/backend/app/models/student_profile.py`

Define a SQLAlchemy model `StudentProfile` mapped to table `student_profiles`:
- `id` — UUID primary key, default uuid4
- `user_id` — UUID, FK to `users.id`, unique (one profile per student)
- `interests` — JSON column, list of strings (e.g., ["machine learning", "web dev", "data science"])
- `strengths` — JSON column, list of strings (e.g., ["mathematics", "programming", "communication"])
- `career_goals` — JSON column, list of strings (e.g., ["software engineer", "data analyst"])
- `preferred_study_style` — String, one of "visual", "reading", "hands-on", "group", "mixed"
- `daily_study_hours_target` — Integer, default 2 (how many hours the student aims to study outside class)
- `created_at` — DateTime, not null
- `updated_at` — DateTime, not null

Add a `__tablename__ = "student_profiles"` and proper relationship to User model.

**Register model in:** `apps/backend/app/models/__init__.py`

Import and add `StudentProfile` to the models list.

**Create migration:** `apps/backend/alembic/versions/006_add_student_profiles.py`

Create the `student_profiles` table with an index on `user_id`.

---

### 1.2 — StudentGoal Model

**Create file:** `apps/backend/app/models/student_goal.py`

Define a SQLAlchemy model `StudentGoal` mapped to table `student_goals`:
- `id` — UUID primary key
- `student_id` — UUID, FK to `users.id`, not null
- `title` — String(200), not null (e.g., "Complete ML course on Coursera")
- `description` — Text, nullable
- `category` — String(50), not null — one of "academic", "career", "skill", "project", "exam_prep"
- `priority` — String(20), default "medium" — one of "low", "medium", "high"
- `target_date` — Date, nullable (deadline)
- `estimated_hours` — Integer, nullable (total hours needed)
- `completed_hours` — Integer, default 0 (hours logged so far)
- `status` — String(20), default "active" — one of "active", "completed", "paused", "abandoned"
- `milestones` — JSON column, list of objects each with `title` (string) and `completed` (boolean)
- `created_at` — DateTime, not null
- `updated_at` — DateTime, not null

Add index on `(student_id, status)` for fast lookups of active goals.

**Register model in:** `apps/backend/app/models/__init__.py`

**Create migration:** `apps/backend/alembic/versions/007_add_student_goals.py`

---

### 1.3 — Student Profile & Goals Schemas

**Create file:** `apps/backend/app/schemas/student_profile.py`

Pydantic schemas:
- `StudentProfileCreate` — interests (list[str]), strengths (list[str]), career_goals (list[str]), preferred_study_style (optional str), daily_study_hours_target (optional int)
- `StudentProfileUpdate` — all fields optional
- `StudentProfileResponse` — all fields + id + user_id + created_at + updated_at, from_attributes=True
- `StudentGoalCreate` — title (required), description, category (required), priority, target_date, estimated_hours, milestones (list of {title: str, completed: bool})
- `StudentGoalUpdate` — all optional except cannot change student_id
- `StudentGoalResponse` — all fields + from_attributes=True
- `GoalProgressUpdate` — completed_hours (int), milestone_index (optional int, to mark a specific milestone done)
- `StudentGoalsListResponse` — items (list), total (int)

---

### 1.4 — Student Profile API

**Create file:** `apps/backend/app/api/v1/student_profile.py`

Endpoints (all require authentication):

**Profile endpoints:**
- `GET /api/v1/students/me/profile` — Return current student's profile. If no profile exists, return 404.
- `POST /api/v1/students/me/profile` — Create profile for current student. Return 409 if already exists.
- `PUT /api/v1/students/me/profile` — Update profile. Merge: only provided fields are updated, existing list fields are replaced (not appended).

**Goal endpoints:**
- `GET /api/v1/students/me/goals` — List current student's goals. Filter by `status` query param (default "active"). Paginated. Ordered by priority (high first) then target_date (soonest first).
- `POST /api/v1/students/me/goals` — Create a new goal for current student.
- `GET /api/v1/students/me/goals/{goal_id}` — Get single goal. Must belong to current student (403 otherwise).
- `PUT /api/v1/students/me/goals/{goal_id}` — Update goal fields.
- `PATCH /api/v1/students/me/goals/{goal_id}/progress` — Update progress. Accept `GoalProgressUpdate`. Increment `completed_hours` by the provided amount. If `milestone_index` is provided, set that milestone's `completed` to true. If all milestones are completed, auto-set status to "completed".
- `DELETE /api/v1/students/me/goals/{goal_id}` — Soft-delete: set status to "abandoned".

**Admin/faculty read-only endpoints:**
- `GET /api/v1/students/{student_id}/profile` — Admin or faculty can view any student's profile.
- `GET /api/v1/students/{student_id}/goals` — Admin or faculty can view any student's goals.

**Register router in:** `apps/backend/app/main.py`

Add prefix `/api/v1/students`, tag "Student Profile".

---

### 1.5 — Student Profile & Goals Tests

**Create file:** `apps/backend/tests/test_student_profile.py`

Tests:
- Create profile returns 201, duplicate returns 409
- Get profile returns data, non-existent returns 404
- Update profile merges correctly (replaces lists, updates scalars)
- Create goal returns 201
- List goals returns only active by default, filter by status works
- Update goal works for owner, returns 403 for other students
- Progress update increments completed_hours
- Progress update with milestone_index marks milestone done
- When all milestones completed, status auto-sets to "completed"
- Admin can read any student's profile and goals

**Verify:** `pytest tests/test_student_profile.py -v` — all pass.

---

### 1.6 — Frontend: Student Profile Page

**Create file:** `apps/frontend/src/views/profile.js`

Build a view with two tabs: "My Profile" and "My Goals".

**My Profile tab:**
- Display current profile if exists, or a "Create Your Profile" prompt.
- Editable form with: interests (tag input — type and press Enter to add, click X to remove), strengths (same tag input), career_goals (same tag input), preferred_study_style (dropdown: Visual, Reading, Hands-on, Group, Mixed), daily_study_hours_target (number input).
- Save button calls POST or PUT depending on whether profile exists.
- Show success toast on save.

**My Goals tab:**
- List of goals in card format (not table). Each card shows: title, category badge, priority badge (color-coded), progress bar (completed_hours / estimated_hours), target date, status.
- "Add Goal" button opens a modal with fields: title, description, category (dropdown), priority (dropdown), target_date (date picker), estimated_hours, milestones (dynamic list — "Add milestone" button to add rows).
- Click a goal card to expand and see: full description, milestones checklist (click to toggle), progress update form (input hours + "Log Hours" button).
- Filter toggle: Active / Completed / All.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `profileApi`: `getMy()`, `create(data)`, `update(data)`.
Add `goalsApi`: `list(params)`, `create(data)`, `get(id)`, `update(id, data)`, `updateProgress(id, data)`, `delete(id)`, `listForStudent(studentId, params)`.

**Add to nav:** Add `{ id: 'profile', label: 'My Profile', icon: 'user-circle' }` to student NAV.

**Verify:** Login as student, create profile with interests/goals, add goals with milestones, log progress, verify milestones auto-complete.

---

## Feature 2 — Free Period Task Suggestions

### 2.1 — Free Period Detection Service

**Create file:** `apps/backend/app/services/free_period_service.py`

Class `FreePeriodService` with methods:

`detect_free_periods(student_id: UUID, target_date: date) -> list[dict]`
- Fetch the student's enrollments (course IDs).
- Fetch all timetable slots for those courses where `day_of_week` matches `target_date.weekday()`.
- Sort slots by `start_time`.
- Define the "campus day" as 08:00 to 18:00 (configurable).
- Find gaps between consecutive slots that are at least 30 minutes long.
- Also find gaps before the first slot and after the last slot (within campus day bounds).
- Return list of dicts: `{ start_time, end_time, duration_minutes }`.

`get_free_periods_for_week(student_id: UUID, week_start: date) -> dict`
- Call `detect_free_periods` for each day of the week (Mon-Fri).
- Return dict keyed by date string ("YYYY-MM-DD") with list of free period dicts.

---

### 2.2 — Task Suggestion Engine

**Create file:** `apps/backend/app/services/task_suggestion_service.py`

**Create file:** `apps/backend/app/services/llm_client.py`

A lightweight wrapper around an LLM API (OpenAI GPT-4o-mini by default, configurable to Claude Haiku, Gemini Flash, or local Ollama). This client is shared by both the task suggestion engine and the daily routine generator.

**Modify file:** `apps/backend/app/core/config.py`

Add settings: `openrouter_api_key: str = ""`, `openrouter_model: str = "openai/gpt-4o-mini"`, `openrouter_base_url: str = "https://openrouter.ai/api/v1"`, `llm_max_tokens: int = 1000`.

OpenRouter uses an OpenAI-compatible API. One key, one endpoint, access to hundreds of models. Popular cheap options: `openai/gpt-4o-mini`, `anthropic/claude-3.5-haiku`, `google/gemini-2.0-flash-001`, `meta-llama/llama-3.1-8b-instruct`. The user sets their preferred model in config.

**`llm_client.py` implementation:**

Class `LLMClient`:
- `__init__` — load api_key, model, base_url, max_tokens from settings
- `async chat(system_prompt: str, user_prompt: str, response_format: str = "json") -> dict`
  - Build request body: `{"model": settings.openrouter_model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}], "max_tokens": settings.llm_max_tokens, "temperature": 0.7}`.
  - If `response_format` is "json", append `"\n\nRespond with valid JSON only."` to the system prompt. (OpenRouter passes this through to the model; `response_format` parameter is model-dependent.)
  - POST to `{settings.openrouter_base_url}/chat/completions` with headers: `Authorization: Bearer {api_key}`, `Content-Type: application/json`, `HTTP-Referer: https://smartattend.in` (OpenRouter requires a referer).
  - Use `httpx.AsyncClient` with a 15-second timeout.
  - Parse `response.choices[0].message.content` as JSON. If parsing fails, retry once with `temperature: 0` (more deterministic). If still fails, raise `LLMServiceError`.
  - On HTTP error (429 rate limit, 500, timeout), raise `LLMServiceError`.

No SDK dependency — just `httpx` which is already in the project.

Class `LLMServiceError(Exception)` — raised when LLM call fails.

**`task_suggestion_service.py` implementation:**

Class `TaskSuggestionService`:

`__init__(self, llm_client: LLMClient, db: AsyncSession)`

`async suggest_tasks(student_id: UUID, free_period: dict, profile: StudentProfile, active_goals: list[StudentGoal], enrolled_courses: list[dict]) -> list[dict]`

Logic:
1. Build a structured context object containing:
   - Student profile: interests, strengths, career_goals, preferred_study_style
   - Active goals: title, category, priority, completed_hours/estimated_hours, milestones (incomplete only), target_date, days_remaining
   - Enrolled courses: course name, recent topics covered (if available from session data)
   - Free period: start_time, end_time, duration_minutes
   - Today's date, day of week

2. Build the LLM prompt:

   System prompt:
   "You are an academic advisor AI for Indian college students. You suggest productive study tasks for free periods between classes. You consider the student's interests, strengths, career goals, active goals with deadlines, and the available time. Always respond with valid JSON only."

   User prompt (structured):
   "Student context: {profile_json}
   Active goals: {goals_json}
   Enrolled courses: {courses_json}
   Free period: {free_period_json}

   Suggest 2-3 specific, actionable tasks the student should do during this free period. For each suggestion, provide:
   - title: short actionable title
   - description: 2-3 sentence specific instruction (what exactly to do, not vague advice)
   - category: one of [academic, career, skill, project, exam_prep, general]
   - duration_minutes: how long to spend (must fit within the free period)
   - linked_goal_title: which active goal this advances (or null if general)
   - priority_score: 0.0-1.0 how strongly you recommend this (higher = more important)
   - reasoning: one sentence explaining why this task fits this student

   Respond as JSON: {\"suggestions\": [{...}, ...]}"

3. Call `llm_client.chat(system_prompt, user_prompt)`.

4. Parse the response. For each suggestion, resolve `linked_goal_title` to an actual `goal_id` by fuzzy-matching against the active goals list. If no match, set goal_id to null.

5. Sort by priority_score descending.

6. If the LLM call fails (LLMServiceError), fall back to a simple rule-based fallback:
   - Short gap (≤45 min): "Review notes for {next_course}"
   - Medium gap (45-90 min): "Work on {highest_priority_goal.title}"
   - Long gap (90+ min): "Deep work on {highest_priority_goal.title}"
   - This ensures the app never breaks if the LLM is down.

7. Return the list of suggestion dicts.

**Caching layer:**
- Before calling the LLM, compute a cache key: `suggestions:{student_id}:{date}:{free_period_start}`.
- Check Redis for cached suggestions (TTL: 4 hours). If found, return cached.
- After getting LLM response, cache it in Redis with 4-hour TTL.
- This avoids repeated LLM calls for the same student + same day.

**When no profile exists:**
- Still call the LLM but with a reduced context (only enrolled courses + free period).
- Add to the prompt: "The student has not completed their profile yet. Suggest general productive study tasks based on their enrolled courses."
- Set `profile_incomplete: true` in the response.

---

### 2.3 — Free Period API Endpoint

**Modify file:** `apps/backend/app/api/v1/student_profile.py` (or create a new file `apps/backend/app/api/v1/daily_plan.py`)

Endpoints:
- `GET /api/v1/students/me/free-periods?date=YYYY-MM-DD` — Return free periods for a given date with task suggestions inline.
- `GET /api/v1/students/me/free-periods/week?week_start=YYYY-MM-DD` — Return free periods for the whole week.

Response shape for a single day:
```
{
  "date": "2026-06-18",
  "classes": [
    { "course_name": "...", "start_time": "09:00", "end_time": "10:00", "room": "..." }
  ],
  "free_periods": [
    {
      "start_time": "10:00",
      "end_time": "11:30",
      "duration_minutes": 90,
      "suggestions": [
        {
          "title": "Work on ML project milestone",
          "description": "Focus on implementing the data preprocessing pipeline...",
          "category": "project",
          "duration_minutes": 90,
          "goal_id": "uuid-of-linked-goal",
          "priority_score": 0.92
        },
        ...
      ]
    }
  ]
}
```

If the student has no profile, the endpoint still works — returns free periods with generic suggestions and a hint: `"profile_incomplete": true`.

**Write tests in:** `apps/backend/tests/test_free_periods.py`

Tests:
- Student with classes at 9-10 and 12-13 gets a free period 10:00-12:00 and 13:00-18:00
- Gaps shorter than 30 minutes are excluded
- Suggestions are returned with valid priority_score
- Student with no profile gets generic suggestions + profile_incomplete flag
- Week view returns all 5 weekdays
- LLM calls must be mocked in all tests — use `unittest.mock.patch` on `LLMClient.chat` to return a pre-built JSON response dict. Do NOT make real API calls in tests.
- Test LLM fallback: mock `LLMClient.chat` to raise `LLMServiceError`, verify rule-based fallback suggestions are returned instead.
- Test caching: call suggest_tasks twice for the same student+date+period, verify second call hits Redis cache (mock Redis get/set).

**Verify:** `pytest tests/test_free_periods.py -v`

---

### 2.4 — Frontend: Free Period Suggestions on Daily Plan

**Create file:** `apps/frontend/src/views/daily-plan.js`

Build a view that shows the student's day:

**Layout:**
- Date selector at top (today by default, with prev/next day arrows).
- A vertical timeline from 08:00 to 18:00.
- Scheduled classes rendered as solid blocks (colored by course, showing course name + room + time).
- Free periods rendered as dashed-outline blocks with a "Suggestions" label.
- Clicking a free period block expands it to show the task suggestion cards.
- Each suggestion card: title, description, duration badge, category badge, linked goal name (if any), "Start" button (marks it as a planned task — stores in localStorage for now).
- If profile_incomplete is true, show a banner: "Complete your profile to get personalized suggestions" with a link to the profile page.
- At the bottom: "Today's Goals" section showing active goals with progress bars.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `dailyPlanApi`: `getFreePeriods(date)`, `getFreePeriodsWeek(weekStart)`.

**Add to nav:** Replace or rename the student's "Schedule" nav item to `{ id: 'daily-plan', label: 'My Day', icon: 'calendar-clock' }` pointing to this view. This replaces the basic schedule view with the richer daily plan.

**Verify:** Login as student with profile and goals, view daily plan, verify free periods show suggestions. Login as student without profile, verify "complete your profile" banner.

---

## Feature 3 — Daily Routine Generator

### 3.1 — Daily Routine Service

**Create file:** `apps/backend/app/services/daily_routine_service.py`

Class `DailyRoutineService`:

`__init__(self, llm_client: LLMClient, db: AsyncSession)`

`async generate_daily_routine(student_id: UUID, target_date: date) -> dict`

Logic:
1. Fetch all data needed:
   - Student's timetable slots for the day (same as free period service).
   - Student's active goals with progress details.
   - Student's profile (interests, strengths, career_goals, study style, daily study hours target).
   - Enrolled courses with recent session data (topics covered, attendance status).
   - Detect free periods (reuse `FreePeriodService.detect_free_periods`).
   - Today's existing attendance records (to know which classes already happened).

2. Build a comprehensive context object for the LLM:
   - Full class schedule for the day with times, courses, rooms.
   - All free periods with durations.
   - Student profile details.
   - Active goals with: title, description, category, priority, completed_hours, estimated_hours, days_remaining, incomplete milestones.
   - Recent academic context: attendance percentage per course, any low-attendance warnings, recent topics covered.
   - Target study hours for the day.
   - Current time (to avoid scheduling in the past).

3. Build the LLM prompt:

   System prompt:
   "You are an intelligent academic planner AI for Indian college students. You create optimized daily routines that balance class attendance, focused study sessions, goal progress, and necessary breaks. You understand Indian college culture (lunch timing, commute patterns, exam pressure). You always respond with valid JSON only."

   User prompt (structured):
   "Create an optimized daily routine for this student.

   Date: {date} ({day_of_week})
   Current time: {current_time}

   Student profile:
   {profile_json}

   Today's classes (fixed — cannot be moved):
   {classes_json}

   Available free periods:
   {free_periods_json}

   Active goals (ordered by priority):
   {goals_json}

   Recent academic context:
   - Attendance percentages per course
   - Topics recently covered
   - Any low-attendance warnings

   Target study hours today: {daily_study_hours_target}

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
   10. Total study time should be close to but not exceed {daily_study_hours_target} hours.

   Respond as JSON:
   {
     \"routine\": [
       {\"type\": \"class\", \"start\": \"HH:MM\", \"end\": \"HH:MM\", \"course_name\": \"...\", \"room\": \"...\", \"note\": \"optional tip about this class\"},
       {\"type\": \"study\", \"start\": \"HH:MM\", \"end\": \"HH:MM\", \"title\": \"specific task title\", \"description\": \"2-3 sentences: exactly what to do, how to approach it, what to focus on\", \"category\": \"...\", \"goal_id\": \"...\", \"goal_title\": \"...\", \"difficulty\": \"easy|medium|hard\"},
       {\"type\": \"break\", \"start\": \"HH:MM\", \"end\": \"HH:MM\", \"title\": \"Lunch break\" or \"Short break\", \"suggestion\": \"optional: quick activity for the break\"},
       {\"type\": \"free\", \"start\": \"HH:MM\", \"end\": \"HH:MM\", \"title\": \"Rest / personal time\", \"optional_suggestions\": [\"light suggestion 1\", \"light suggestion 2\"]}
     ],
     \"summary\": {
       \"total_classes\": N,
       \"total_study_hours\": N.N,
       \"total_break_hours\": N.N,
       \"total_free_hours\": N.N,
       \"goals_addressed\": [\"goal title 1\", \"goal title 2\"],
       \"daily_tip\": \"one motivational/strategic tip tailored to this student's situation\"
     },
     \"goal_progress_today\": [
       {\"goal_id\": \"...\", \"goal_title\": \"...\", \"hours_planned\": N.N, \"hours_remaining\": N.N, \"milestones_to_work_on\": [\"milestone title\"]}
     ]
   }"

4. Call `llm_client.chat(system_prompt, user_prompt)`.

5. Parse the response. Validate:
   - All time blocks are in chronological order.
   - No overlapping time blocks.
   - Class blocks match the actual timetable (LLM didn't modify them).
   - Total study time does not exceed target by more than 10%.
   - If validation fails, fix programmatically (re-sort, trim excess study time from the last block).

6. Resolve `goal_id` references — the LLM returns `goal_title`, match back to actual UUIDs.

7. If LLM call fails (LLMServiceError), fall back to a deterministic planner:
   - Fill free periods with a simple greedy algorithm: assign the highest-priority goal to each free period.
   - Insert lunch at 12:30 if free.
   - Use `TaskSuggestionService` (which has its own LLM call, or its own fallback) for task titles.
   - Mark response with `"generated_by": "fallback"` so the frontend can show "Basic plan — AI planner unavailable".

**Caching:**
- Cache key: `routine:{student_id}:{date}`.
- TTL: 4 hours (same as suggestions — regenerate if student logs new goal progress).
- Invalidate cache when: student updates profile, logs goal progress, or a class session status changes.
- On cache hit, return with `"generated_by": "cached"`.

**When no profile exists:**
- Call the LLM with reduced context (classes + enrolled courses only).
- Prompt adds: "The student has not set up their profile yet. Create a basic study routine based on their enrolled courses. Include a suggestion to complete their profile."
- Set `profile_incomplete: true` in response.

---

### 3.2 — Daily Routine API Endpoint

**Modify file:** `apps/backend/app/api/v1/daily_plan.py`

Add endpoints:
- `GET /api/v1/students/me/routine?date=YYYY-MM-DD` — Generate and return the full daily routine.
- `GET /api/v1/students/me/routine/weekly?week_start=YYYY-MM-DD` — Return routines for Mon-Fri.

The routine endpoint calls `DailyRoutineService.generate_daily_routine` which internally uses `FreePeriodService` and `TaskSuggestionService`.

If no profile exists, return a basic routine (classes only + generic free time) with `profile_incomplete: true`.

**Write tests in:** `apps/backend/tests/test_daily_routine.py`

Tests:
- Routine includes all classes in chronological order
- Free periods are filled with study blocks up to daily_study_hours_target
- Lunch break is inserted at 12:30 if that time is free
- Goal with completed status is not allocated study time
- Total planned hours does not exceed target
- Unallocated time appears as "free" blocks
- Student with no profile gets basic routine with profile_incomplete flag
- Weekly view returns 5 days
- LLM calls must be mocked — use `unittest.mock.patch` on `LLMClient.chat` to return a pre-built routine JSON. Do NOT make real API calls in tests.
- Test LLM fallback: mock `LLMClient.chat` to raise `LLMServiceError`, verify deterministic fallback generates a valid routine with `"generated_by": "fallback"`.
- Test validation: mock LLM response with overlapping times, verify the service fixes them programmatically.
- Test caching: generate routine twice for same student+date, verify second call returns cached result with `"generated_by": "cached"`.
- Test cache invalidation: generate routine, then log goal progress, then generate again — verify a new LLM call is made (cache was invalidated).

**Verify:** `pytest tests/test_daily_routine.py -v`

---

### 3.3 — Frontend: Daily Routine View

**Modify file:** `apps/frontend/src/views/daily-plan.js` (same file from Feature 2)

Add a "Routine" tab next to the "Free Periods" tab in the daily plan view:

**Routine tab layout:**
- Date selector (same as free periods tab, keep in sync).
- A clean vertical timeline showing the full day.
- Color-coded blocks: blue for classes, green for study sessions, gray for breaks, white/outline for unallocated.
- Each block shows: time range, title, duration.
- Study blocks show: linked goal name, category badge, description (expandable).
- At the top: summary card — "Today's Plan: 3 classes, 2.5h study planned, 0.5h free time".
- At the bottom: "Goal Progress Today" — horizontal bars for each goal being worked on.
- A "Regenerate" button that re-fetches the routine (useful after goal changes).

**Also show the routine on the dashboard:**
- Modify `apps/frontend/src/views/dashboard.js` — for student role, add a "Today's Routine" card at the top showing the next 3 items in the routine (current block highlighted).

**Verify:** Login as student, view daily routine, verify classes and study sessions appear. Change a goal priority, regenerate, verify the routine updates.

---

## Feature 4 — Classroom Display Screen

### 4.1 — Display Token & Endpoint

**Create file:** `apps/backend/app/api/v1/display.py`

Endpoints:
- `GET /api/v1/sessions/{session_id}/display-token` — Faculty only. Generate a short-lived display token (JWT, 4-hour expiry, scoped to this session only). Return `{ display_token: "..." }`. The token contains only `session_id` and `exp` — no user info.
- `GET /api/v1/display/session/{session_id}` — Accept display_token in query param `?token=XXX`. Validate the token. Return session info: course_name, start_time, room, total_enrolled, present_count, present_percentage, and a list of present students (name, roll_number, marked_at — no sensitive data).

**Register router in:** `apps/backend/app/main.py`

Add prefix `/api/v1/display`, tag "Display".

---

### 4.2 — Frontend: Classroom Display Page

**Create file:** `apps/frontend/src/views/classroom-display.html`

This is a **standalone HTML page** (not inside the SPA router) designed for projection on a large screen:

**Design requirements:**
- Full-screen, dark background (dark navy or charcoal), large white text.
- No sidebar, no navigation, no login — just the display.
- URL pattern: `/classroom-display.html?session_id=XXX&token=XXX`

**Layout:**
- Top: Course name + session time (large font, 24-32px).
- Center: Live attendance counter — large animated number showing "X / Y present (Z%)" with a circular progress ring.
- Below center: scrolling list of checked-in students (name + roll number), most recent at top. New entries slide in from the right with a subtle animation.
- Bottom-right: session duration timer (counting up from session start).
- Bottom-left: "SmartAttend" logo text.

**Real-time updates:**
- On page load, fetch initial data from `GET /api/v1/display/session/{session_id}?token=XXX`.
- Open WebSocket connection to `ws://host/ws/session/{session_id}` (the existing session WebSocket).
- On each attendance event, update the counter, add the student name to the scrolling list with animation.
- If WebSocket disconnects, show "Reconnecting..." overlay, auto-reconnect with backoff.

**Auto-refresh:** If the page has been open for more than 3 hours, re-fetch the display token (or show "Session ended" if the session is no longer active).

**CSS:** Use CSS animations for the student list (slide-in), the counter (count-up animation when number changes), and the progress ring (smooth transition).

---

### 4.3 — Frontend: Generate Display Link (Faculty)

**Modify file:** `apps/frontend/src/views/sessions.js`

For active sessions (status = "active"), add a "Display" button:
- On click, call `GET /api/v1/sessions/{id}/display-token`.
- Show a modal with: the full display URL, a "Copy Link" button, and a "Open in New Tab" button.
- Instructions text: "Project this link on the classroom screen. Students will see their attendance update in real-time."

**Modify file:** `apps/frontend/src/views/live-session.js`

In the faculty live session view, add a "Projector Mode" button at the top that opens the classroom display URL in a new tab.

**Add to API client:** `apps/frontend/src/utils/api.js`

Add `displayApi`: `getToken(sessionId)`, `getSession(sessionId, token)`.

**Verify:** Start a session as faculty, click "Display" button, copy the URL, open it in a new tab, mark attendance as a student, verify the display screen updates in real-time.

---

### 4.4 — WebSocket Handler for Display

**Modify file:** `apps/backend/app/websocket/handlers.py`

The existing session WebSocket at `/ws/session/{session_id}` already broadcasts attendance events. No changes needed to the handler itself — the display page just connects as a listener.

However, verify that the broadcast message shape includes: `student_name`, `roll_number`, `marked_at`, `status`, `present_count`, `total_enrolled`. If any fields are missing from the broadcast payload, add them.

---

## Database Migrations Summary

| Migration | Tables | File |
|-----------|--------|------|
| 006 | `student_profiles` | `alembic/versions/006_add_student_profiles.py` |
| 007 | `student_goals` | `alembic/versions/007_add_student_goals.py` |

Both migrations should be run with `cd apps/backend && alembic upgrade head`.

---

## File Summary — All New Files

| File | Purpose |
|------|---------|
| `apps/backend/app/models/student_profile.py` | StudentProfile model |
| `apps/backend/app/models/student_goal.py` | StudentGoal model |
| `apps/backend/app/schemas/student_profile.py` | Pydantic schemas for profile + goals |
| `apps/backend/app/api/v1/student_profile.py` | Profile + goals REST API |
| `apps/backend/app/api/v1/daily_plan.py` | Free periods + routine API |
| `apps/backend/app/api/v1/display.py` | Classroom display API |
| `apps/backend/app/services/llm_client.py` | OpenRouter LLM client (shared by suggestion + routine services) |
| `apps/backend/app/services/free_period_service.py` | Free period detection logic |
| `apps/backend/app/services/task_suggestion_service.py` | LLM-powered task suggestion engine |
| `apps/backend/app/services/daily_routine_service.py` | LLM-powered daily routine generator |
| `apps/backend/alembic/versions/006_add_student_profiles.py` | Migration |
| `apps/backend/alembic/versions/007_add_student_goals.py` | Migration |
| `apps/backend/tests/test_student_profile.py` | Profile + goals tests |
| `apps/backend/tests/test_free_periods.py` | Free period tests |
| `apps/backend/tests/test_daily_routine.py` | Routine tests |
| `apps/frontend/src/views/profile.js` | Student profile + goals UI |
| `apps/frontend/src/views/daily-plan.js` | Daily plan + routine UI |
| `apps/frontend/src/views/classroom-display.html` | Standalone projector display |

## Files to Modify

| File | Change |
|------|--------|
| `apps/backend/app/models/__init__.py` | Register new models |
| `apps/backend/app/main.py` | Register new routers |
| `apps/frontend/src/utils/api.js` | Add profileApi, goalsApi, dailyPlanApi, displayApi |
| `apps/frontend/src/app.js` | Add new nav items, register views |
| `apps/frontend/src/views/sessions.js` | Add "Display" button for active sessions |
| `apps/frontend/src/views/live-session.js` | Add "Projector Mode" button |
| `apps/frontend/src/views/dashboard.js` | Add "Today's Routine" card for students |
| `apps/backend/app/websocket/handlers.py` | Verify broadcast payload completeness |

---

## Build Order

Execute in this order to minimize blocked dependencies:

1. Models + migrations (1.1, 1.2) — no dependencies
2. Schemas (1.3) — depends on models
3. Profile + Goals API (1.4) — depends on schemas
4. Profile + Goals tests (1.5) — verify API works
5. LLM client (2.2 — `llm_client.py`) — no dependencies, shared infrastructure
6. Free period service (2.1) — depends on timetable models (already exist)
7. Task suggestion service (2.2 — `task_suggestion_service.py`) — depends on LLM client + profile model
8. Free period API + tests (2.3) — depends on services
9. Daily routine service (3.1) — depends on LLM client + free period + suggestion services
10. Daily routine API + tests (3.2) — depends on routine service
11. Display token + API (4.1) — independent, can be done in parallel with 6-10
12. Frontend: profile page (1.6) — depends on API being done
13. Frontend: daily plan (2.4, 3.3) — depends on APIs being done
14. Frontend: classroom display (4.2, 4.3, 4.4) — depends on display API
15. Run full test suite: `make test` — verify nothing is broken

**Environment setup (before step 5):**
Add to `.env`:
```
OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx
OPENROUTER_MODEL=openai/gpt-4o-mini
```
The LLM client reads these from settings. Tests mock the LLM call so no key is needed for testing.

---

## Verification Checklist

After all tasks are complete, verify these end-to-end flows:

- [ ] Student creates profile with interests, strengths, career goals
- [ ] Student adds 3 goals with milestones and target dates
- [ ] Student views daily plan — sees free periods with personalized suggestions
- [ ] Student views daily routine — sees classes + study blocks + lunch break + free time
- [ ] Goal progress updates work, milestones toggle, auto-complete triggers
- [ ] Faculty starts a session, gets a display link, opens it on projector
- [ ] Student marks attendance → display screen updates in real-time
- [ ] Student without a profile still sees basic daily plan with "complete profile" hint
- [ ] LLM fallback works: stop the LLM (wrong API key), verify suggestions + routine still work with fallback logic
- [ ] All existing tests still pass (`make test`)
- [ ] New tests pass (`pytest tests/test_student_profile.py tests/test_free_periods.py tests/test_daily_routine.py -v`)
- [ ] Daily routine includes `daily_tip` and `summary` fields from LLM response
