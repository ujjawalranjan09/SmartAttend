from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import (
    get_current_user,
    get_user_institution_id,
    require_faculty,
    require_admin,
)
from app.models.user import User, UserRole
from app.models.course import Course, Enrollment
from app.schemas.course import (
    CourseCreate,
    CourseUpdate,
    CourseResponse,
    CourseListResponse,
    EnrollRequest,
)
from app.services.enrollment_service import EnrollmentService

router = APIRouter()


@router.post("/", response_model=CourseResponse, status_code=201)
async def create_course(
    body: CourseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    faculty_id = body.faculty_id
    if current_user.role in (UserRole.FACULTY, UserRole.HOD) and not faculty_id:
        faculty_id = current_user.id
    elif faculty_id is None:
        raise HTTPException(
            status_code=400, detail="faculty_id is required for admin users"
        )

    course = Course(
        institution_id=body.institution_id,
        department_id=body.department_id,
        faculty_id=faculty_id,
        name=body.name,
        code=body.code,
        semester=body.semester,
        academic_year=body.academic_year,
        min_attendance_pct=body.min_attendance_pct,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return CourseResponse.model_validate(course)


@router.get("/", response_model=CourseListResponse)
async def list_courses(
    institution_id: Optional[UUID] = Query(None),
    department_id: Optional[UUID] = Query(None),
    faculty_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    q = select(Course)
    if institution_id:
        q = q.where(Course.institution_id == institution_id)
    if department_id:
        q = q.where(Course.department_id == department_id)
    if faculty_id:
        q = q.where(Course.faculty_id == faculty_id)

    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar() or 0

    q = (
        q.order_by(Course.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(q)
    courses = result.scalars().all()

    return CourseListResponse(
        items=[CourseResponse.model_validate(c) for c in courses],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{course_id}")
async def get_course(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    count_result = await db.execute(
        select(func.count()).where(Enrollment.course_id == course_id)
    )
    enrollment_count = count_result.scalar() or 0

    data = CourseResponse.model_validate(course).model_dump()
    data["enrollment_count"] = enrollment_count
    return data


@router.put("/{course_id}", response_model=CourseResponse)
async def update_course(
    course_id: UUID,
    body: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if (
        current_user.role in (UserRole.FACULTY, UserRole.HOD)
        and course.faculty_id != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="Cannot update another faculty's course"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(course, field, value)

    await db.commit()
    await db.refresh(course)
    return CourseResponse.model_validate(course)


@router.get("/{course_id}/students")
async def list_enrolled_students(
    course_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    q = (
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.course_id == course_id)
    )
    result = await db.execute(q)
    students = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "full_name": s.full_name,
            "roll_number": s.roll_number,
            "email": s.email,
        }
        for s in students
    ]


@router.post("/{course_id}/enroll")
async def enroll_students(
    course_id: UUID,
    body: EnrollRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    existing_q = select(Enrollment.student_id).where(
        Enrollment.course_id == course_id,
        Enrollment.student_id.in_(body.student_ids),
    )
    existing_result = await db.execute(existing_q)
    already_enrolled = {row[0] for row in existing_result.all()}

    enrolled, skipped = 0, 0
    for student_id in body.student_ids:
        if student_id in already_enrolled:
            skipped += 1
            continue
        db.add(Enrollment(student_id=student_id, course_id=course_id))
        enrolled += 1

    await db.commit()
    return {"enrolled": enrolled, "skipped": skipped}


@router.post("/{course_id}/enroll/csv")
async def enroll_from_csv(
    course_id: UUID,
    upload_file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_faculty),
):
    result = await db.execute(select(Course).where(Course.id == course_id))
    course = result.scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    if (
        current_user.role in (UserRole.FACULTY, UserRole.HOD)
        and course.faculty_id != current_user.id
    ):
        raise HTTPException(
            status_code=403, detail="Cannot enroll students in another faculty's course"
        )

    try:
        content = (await upload_file.read()).decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")

    try:
        service = EnrollmentService(db)
        return await service.bulk_enroll_from_csv(course_id, content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{course_id}/enroll/{student_id}")
async def unenroll_student(
    course_id: UUID,
    student_id: UUID,
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_faculty),
):
    result = await db.execute(
        select(Enrollment).where(
            Enrollment.course_id == course_id,
            Enrollment.student_id == student_id,
        )
    )
    enrollment = result.scalar_one_or_none()
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    await db.delete(enrollment)
    await db.commit()
    return {"removed": True}
