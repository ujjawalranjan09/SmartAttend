from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.attributes import flag_modified

from app.core.database import get_db
from app.core.deps import get_current_user, require_faculty
from app.models.user import User, UserRole
from app.models.student_profile import StudentProfile
from app.models.student_goal import StudentGoal
from app.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileUpdate,
    StudentProfileResponse,
    StudentGoalCreate,
    StudentGoalUpdate,
    StudentGoalResponse,
    GoalProgressUpdate,
    StudentGoalsListResponse,
)

router = APIRouter()


# ─── Helpers ──────────────────────────────────────────────────────────────────


async def _get_profile(db: AsyncSession, user_id: UUID) -> StudentProfile | None:
    result = await db.execute(
        select(StudentProfile).where(StudentProfile.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _get_or_404(db: AsyncSession, goal_id: UUID, user_id: UUID) -> StudentGoal:
    result = await db.execute(
        select(StudentGoal).where(
            StudentGoal.id == goal_id,
            StudentGoal.student_id == user_id,
        )
    )
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


# ─── Profile Endpoints ────────────────────────────────────────────────────────


@router.get("/me/profile", response_model=StudentProfileResponse)
async def get_my_profile(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return current student's profile. Returns 404 if no profile exists."""
    profile = await _get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return StudentProfileResponse.model_validate(profile)


@router.post("/me/profile", response_model=StudentProfileResponse, status_code=201)
async def create_my_profile(
    body: StudentProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create profile for current student. Returns 409 if already exists."""
    existing = await _get_profile(db, current_user.id)
    if existing:
        raise HTTPException(status_code=409, detail="Profile already exists")
    profile = StudentProfile(
        user_id=current_user.id,
        interests=body.interests,
        strengths=body.strengths,
        career_goals=body.career_goals,
        preferred_study_style=body.preferred_study_style,
        daily_study_hours_target=body.daily_study_hours_target,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return StudentProfileResponse.model_validate(profile)


@router.put("/me/profile", response_model=StudentProfileResponse)
async def update_my_profile(
    body: StudentProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update profile. Only provided fields are updated; list fields are replaced."""
    profile = await _get_profile(db, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return StudentProfileResponse.model_validate(profile)


# ─── Goal Endpoints ───────────────────────────────────────────────────────────


@router.get("/me/goals", response_model=StudentGoalsListResponse)
async def list_my_goals(
    status: str = Query("active"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List current student's goals. Filter by status (default: active)."""
    query = (
        select(StudentGoal)
        .where(
            StudentGoal.student_id == current_user.id,
            StudentGoal.status == status,
        )
        .order_by(
            # high priority first
            StudentGoal.priority.desc(),
            # then soonest target_date first (nulls last)
            StudentGoal.target_date.is_(None),
            StudentGoal.target_date.asc(),
        )
    )
    result = await db.execute(query)
    goals = result.scalars().all()
    return StudentGoalsListResponse(
        items=[StudentGoalResponse.model_validate(g) for g in goals],
        total=len(goals),
    )


@router.post("/me/goals", response_model=StudentGoalResponse, status_code=201)
async def create_my_goal(
    body: StudentGoalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new goal for the current student."""
    goal = StudentGoal(
        student_id=current_user.id,
        title=body.title,
        description=body.description,
        category=body.category,
        priority=body.priority,
        target_date=body.target_date,
        estimated_hours=body.estimated_hours,
        milestones=[m.model_dump() for m in body.milestones],
    )
    db.add(goal)
    await db.commit()
    await db.refresh(goal)
    return StudentGoalResponse.model_validate(goal)


@router.get("/me/goals/{goal_id}", response_model=StudentGoalResponse)
async def get_my_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single goal. Must belong to current student."""
    return await _get_or_404(db, goal_id, current_user.id)


@router.put("/me/goals/{goal_id}", response_model=StudentGoalResponse)
async def update_my_goal(
    goal_id: UUID,
    body: StudentGoalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update goal fields. Cannot change student_id."""
    goal = await _get_or_404(db, goal_id, current_user.id)
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "milestones" and value is not None:
            value = [m if isinstance(m, dict) else m.model_dump() for m in value]
        setattr(goal, field, value)
    await db.commit()
    await db.refresh(goal)
    return StudentGoalResponse.model_validate(goal)


@router.patch("/me/goals/{goal_id}/progress", response_model=StudentGoalResponse)
async def update_goal_progress(
    goal_id: UUID,
    body: GoalProgressUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update progress. Increment completed_hours. Mark milestone done by index."""
    goal = await _get_or_404(db, goal_id, current_user.id)
    goal.completed_hours += body.completed_hours

    if body.milestone_index is not None:
        milestones = list(goal.milestones)
        if 0 <= body.milestone_index < len(milestones):
            milestones[body.milestone_index]["completed"] = True
            goal.milestones = milestones
            flag_modified(goal, "milestones")

    # Auto-complete: if all milestones done, set status to completed
    if goal.milestones and all(m.get("completed", False) for m in goal.milestones):
        goal.status = "completed"

    await db.commit()
    await db.refresh(goal)
    return StudentGoalResponse.model_validate(goal)


@router.delete("/me/goals/{goal_id}", status_code=204)
async def delete_my_goal(
    goal_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete: set status to 'abandoned'."""
    goal = await _get_or_404(db, goal_id, current_user.id)
    goal.status = "abandoned"
    await db.commit()


# ─── Admin / Faculty Read-Only Endpoints ─────────────────────────────────────


@router.get("/{student_id}/profile", response_model=StudentProfileResponse)
async def get_student_profile(
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    """Admin or faculty can view any student's profile."""
    profile = await _get_profile(db, student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return StudentProfileResponse.model_validate(profile)


@router.get("/{student_id}/goals", response_model=StudentGoalsListResponse)
async def get_student_goals(
    student_id: UUID,
    status: str = Query("active"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    """Admin or faculty can view any student's goals."""
    query = (
        select(StudentGoal)
        .where(
            StudentGoal.student_id == student_id,
            StudentGoal.status == status,
        )
        .order_by(StudentGoal.priority.desc(), StudentGoal.target_date.asc())
    )
    result = await db.execute(query)
    goals = result.scalars().all()
    return StudentGoalsListResponse(
        items=[StudentGoalResponse.model_validate(g) for g in goals],
        total=len(goals),
    )