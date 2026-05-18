from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional

from app.core.database import get_db
from app.core.deps import require_faculty, require_admin, get_current_user
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate, UserResponse, UserListResponse
from app.services.user_service import UserService
from app.services.session_service import SessionService
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/", response_model=UserListResponse)
async def list_faculty(
    institution_id: UUID = Query(...),
    department_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    svc = UserService(db)
    users, total = await svc.get_all(
        institution_id=institution_id,
        role=UserRole.FACULTY,
        department_id=department_id,
        search=search,
        page=page,
        page_size=page_size,
    )
    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.post("/", response_model=UserResponse, status_code=201)
async def create_faculty(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    if body.role not in (UserRole.FACULTY, UserRole.HOD):
        raise HTTPException(status_code=400, detail="Role must be faculty or hod")
    svc = UserService(db)
    existing = await svc.get_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    user = await svc.create(body)
    return UserResponse.model_validate(user)


@router.get("/{faculty_id}", response_model=UserResponse)
async def get_faculty(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    svc = UserService(db)
    user = await svc.get_by_id(faculty_id)
    if not user or user.role not in (UserRole.FACULTY, UserRole.HOD, UserRole.ADMIN):
        raise HTTPException(status_code=404, detail="Faculty not found")
    return UserResponse.model_validate(user)


@router.put("/{faculty_id}", response_model=UserResponse)
async def update_faculty(
    faculty_id: UUID,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Faculty can update their own profile; admin can update anyone
    if (
        current_user.role not in (UserRole.ADMIN, UserRole.HOD)
        and current_user.id != faculty_id
    ):
        raise HTTPException(
            status_code=403, detail="Cannot update another faculty's profile"
        )
    svc = UserService(db)
    user = await svc.update(faculty_id, body)
    if not user:
        raise HTTPException(status_code=404, detail="Faculty not found")
    return UserResponse.model_validate(user)


@router.delete("/{faculty_id}", status_code=204)
async def deactivate_faculty(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_admin),
):
    svc = UserService(db)
    ok = await svc.deactivate(faculty_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Faculty not found")


@router.get("/{faculty_id}/sessions")
async def get_faculty_sessions(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    svc = SessionService(db)
    sessions = await svc.get_by_faculty(faculty_id)
    return sessions


@router.get("/{faculty_id}/analytics")
async def get_faculty_analytics(
    faculty_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    """Aggregated analytics across all sessions taught by this faculty."""
    session_svc = SessionService(db)
    analytics_svc = AnalyticsService(db)

    sessions = await session_svc.get_by_faculty(faculty_id)
    course_ids = list({s.course_id for s in sessions if s.course_id})

    courses_analytics = []
    for cid in course_ids:
        ca = await analytics_svc.get_course_analytics(cid)
        courses_analytics.append(ca)

    return {
        "faculty_id": str(faculty_id),
        "total_sessions": len(sessions),
        "total_courses": len(course_ids),
        "courses": [c.model_dump() for c in courses_analytics],
    }
