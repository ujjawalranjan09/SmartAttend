"""
Seed script — creates demo institution, faculty, students, course, and sessions.
Run: python scripts/seed_demo.py
"""
import asyncio
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.database import Base
from app.core.security import hash_password
from app.models.institution import Institution, Department
from app.models.user import User, UserRole
from app.models.course import Course, Enrollment
from app.models.session import ClassSession


async def seed():
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as db:
        # Institution
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

        # Department
        dept = Department(
            id=uuid.uuid4(),
            name="Information Technology",
            code="IT",
            institution_id=inst.id,
            created_at=datetime.utcnow(),
        )
        db.add(dept)
        await db.flush()

        # Admin user
        admin = User(
            id=uuid.uuid4(),
            email="admin@smartattend.in",
            full_name="System Admin",
            hashed_password=hash_password("admin123"),
            role=UserRole.ADMIN,
            institution_id=inst.id,
            department_id=dept.id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Faculty
        faculty = User(
            id=uuid.uuid4(),
            email="faculty@smartattend.in",
            full_name="Prof. Ramesh Sharma",
            hashed_password=hash_password("faculty123"),
            role=UserRole.FACULTY,
            institution_id=inst.id,
            department_id=dept.id,
            employee_id="EMP001",
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Students
        students = []
        for i in range(1, 6):
            s = User(
                id=uuid.uuid4(),
                email=f"student{i}@smartattend.in",
                full_name=f"Student {i}",
                hashed_password=hash_password("student123"),
                role=UserRole.STUDENT,
                institution_id=inst.id,
                department_id=dept.id,
                roll_number=f"IT2021{i:03d}",
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(s)
            students.append(s)
        await db.flush()

        # Course
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
