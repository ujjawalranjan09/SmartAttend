"""
Seed script — creates demo institution, faculty, students, course, and sessions.
Run: python scripts/seed_demo.py

Idempotent: re-running won't duplicate rows or fail on existing emails.
"""

import asyncio
import uuid
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.database import Base
from app.core.database import to_async_url
from app.core.security import hash_password
from app.models.institution import Institution, Department
from app.models.user import User, UserRole
from app.models.course import Course, Enrollment
from app.models.session import ClassSession
from app.models.notification import Notification
from app.models.audit_log import AuditLog


def _admin():
    return dict(
        email="admin@smartattend.in",
        full_name="System Admin",
        password="Admin@1234",
        role=UserRole.ADMIN.value,
        employee_id="ADM001",
    )


def _faculty():
    return dict(
        email="faculty@smartattend.in",
        full_name="Prof. Ramesh Sharma",
        password="Faculty@1234",
        role=UserRole.FACULTY.value,
        employee_id="EMP001",
    )


async def _get_or_create_user(db: AsyncSession, inst_id, dept_id, spec: dict) -> User:
    """Return existing user by email, or create one. Demo accounts are verified."""
    existing = (
        await db.execute(select(User).where(User.email == spec["email"]))
    ).scalar_one_or_none()
    if existing:
        return existing
    user = User(
        id=uuid.uuid4(),
        email=spec["email"],
        full_name=spec["full_name"],
        hashed_password=hash_password(spec["password"]),
        role=spec["role"],
        institution_id=inst_id,
        department_id=dept_id,
        employee_id=spec.get("employee_id"),
        is_active=True,
        is_verified=True,  # demo accounts skip email verification
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()
    return user


async def seed():
    # Normalize the URL (postgres:// -> postgresql+asyncpg://) so the async
    # engine gets a valid driver regardless of what DATABASE_URL looks like.
    engine = create_async_engine(to_async_url(settings.database_url), echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        # Institution (idempotent)
        inst = (
            await db.execute(
                select(Institution).where(Institution.short_name == "RTU")
            )
        ).scalar_one_or_none()
        if not inst:
            inst = Institution(
                id=uuid.uuid4(),
                name="Rajasthan Technical University",
                short_name="RTU",
                city="Kota",
                state="Rajasthan",
                created_at=datetime.utcnow(),
            )
            db.add(inst)
            await db.flush()

        # Department (idempotent)
        dept = (
            await db.execute(
                select(Department).where(Department.code == "IT")
            )
        ).scalar_one_or_none()
        if not dept:
            dept = Department(
                id=uuid.uuid4(),
                name="Information Technology",
                code="IT",
                institution_id=inst.id,
                created_at=datetime.utcnow(),
            )
            db.add(dept)
            await db.flush()

        # Admin / Faculty (idempotent)
        admin = await _get_or_create_user(db, inst.id, dept.id, _admin())
        faculty = await _get_or_create_user(db, inst.id, dept.id, _faculty())

        # Students (idempotent by email)
        students = []
        for i in range(1, 6):
            s = await _get_or_create_user(
                db, inst.id, dept.id,
                dict(
                    email=f"student{i}@smartattend.in",
                    full_name=f"Student {i}",
                    password="Student@1234",
                    role=UserRole.STUDENT.value,
                    roll_number=f"IT2021{i:03d}",
                ),
            )
            students.append(s)
        await db.flush()

        # Course (idempotent). Only seed enrollments/sessions/notifications/audit
        # logs when the course is freshly created — otherwise they'd duplicate.
        course = (
            await db.execute(select(Course).where(Course.code == "IT401"))
        ).scalar_one_or_none()
        if not course:
            course = Course(
                id=uuid.uuid4(),
                name="Data Structures & Algorithms",
                code="IT401",
                institution_id=inst.id,
                department_id=dept.id,
                credits=4,
                semester=6,
                is_active=True,
                created_at=datetime.utcnow(),
            )
            db.add(course)
            await db.flush()

            # Enrol students
            for s in students:
                enr = Enrollment(
                    id=uuid.uuid4(),
                    student_id=s.id,
                    course_id=course.id,
                    enrolled_at=datetime.utcnow(),
                )
                db.add(enr)

            # Sessions
            for day_offset in range(5):
                session = ClassSession(
                    id=uuid.uuid4(),
                    course_id=course.id,
                    faculty_id=faculty.id,
                    scheduled_at=datetime.utcnow() - timedelta(days=day_offset),
                    status="completed",
                    room="IT-Lab-3",
                    created_at=datetime.utcnow(),
                )
                db.add(session)

            # Notifications
            notifications = [
                Notification(
                    id=uuid.uuid4(),
                    user_id=students[0].id,
                    title="Upcoming Class",
                    body="Data Structures & Algorithms session tomorrow at 10:00 AM in IT-Lab-3.",
                    type="reminder",
                    is_read=False,
                    created_at=datetime.utcnow(),
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=students[1].id,
                    title="Schedule Changed",
                    body="Your DSA lab has been rescheduled to Friday 2:00 PM.",
                    type="alert",
                    is_read=False,
                    created_at=datetime.utcnow(),
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=faculty.id,
                    title="Attendance Report Ready",
                    body="Attendance report for IT401 has been generated. Check your dashboard.",
                    type="system",
                    is_read=False,
                    created_at=datetime.utcnow(),
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=students[2].id,
                    title="Assignment Due",
                    body="Assignment 3 on Graph Algorithms is due on Friday.",
                    type="reminder",
                    is_read=False,
                    created_at=datetime.utcnow(),
                ),
                Notification(
                    id=uuid.uuid4(),
                    user_id=admin.id,
                    title="New Enrollment",
                    body="5 new students have been enrolled in IT401.",
                    type="system",
                    is_read=False,
                    created_at=datetime.utcnow(),
                ),
            ]
            for n in notifications:
                db.add(n)

            # Audit Logs
            audit_logs = [
                AuditLog(
                    id=uuid.uuid4(),
                    user_id=admin.id,
                    action="User.create",
                    resource_type="user",
                    resource_id=faculty.id,
                    old_value=None,
                    new_value={
                        "email": "faculty@smartattend.in",
                        "role": "faculty",
                        "description": "seed data",
                    },
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow(),
                ),
                AuditLog(
                    id=uuid.uuid4(),
                    user_id=admin.id,
                    action="ClassSession.create",
                    resource_type="class_session",
                    resource_id=None,
                    old_value=None,
                    new_value={
                        "course_code": "IT401",
                        "room": "IT-Lab-3",
                        "description": "seed data",
                    },
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow(),
                ),
                AuditLog(
                    id=uuid.uuid4(),
                    user_id=admin.id,
                    action="Enrollment.create",
                    resource_type="enrollment",
                    resource_id=None,
                    old_value=None,
                    new_value={
                        "course_code": "IT401",
                        "student_count": 5,
                        "description": "seed data",
                    },
                    ip_address="127.0.0.1",
                    created_at=datetime.utcnow(),
                ),
            ]
            for log in audit_logs:
                db.add(log)

        await db.commit()
        print("\n✅ Demo data seeded successfully!")
        print(f"   Institution : {inst.name}")
        print(f"   Admin       : admin@smartattend.in  /  Admin@1234")
        print(f"   Faculty     : faculty@smartattend.in  /  Faculty@1234")
        print(f"   Students    : student1..5@smartattend.in  /  Student@1234")
        print(f"   Course      : {course.name} ({course.code})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
