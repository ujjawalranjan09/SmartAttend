import csv
import io
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course, Enrollment
from app.models.user import User, UserRole


class EnrollmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def bulk_enroll_from_csv(self, course_id: UUID, csv_content: str) -> dict:
        reader = csv.DictReader(io.StringIO(csv_content))
        if not reader.fieldnames:
            raise ValueError("CSV has no headers")

        fieldnames_lower = {f.strip().lower(): f for f in reader.fieldnames}
        email_col = fieldnames_lower.get("email")
        roll_col = fieldnames_lower.get("roll_number")

        if not email_col and not roll_col:
            raise ValueError("CSV must have an 'email' or 'roll_number' column")

        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            raise LookupError("Course not found")

        institution_id = course.institution_id

        existing_q = select(Enrollment.student_id).where(
            Enrollment.course_id == course_id
        )
        existing_result = await self.db.execute(existing_q)
        already_enrolled = {row[0] for row in existing_result.all()}

        enrolled_count = 0
        skipped_count = 0
        not_found: list[str] = []

        for row in reader:
            lookup_value = None
            if email_col:
                lookup_value = row.get(email_col, "").strip()
            elif roll_col:
                lookup_value = row.get(roll_col, "").strip()

            if not lookup_value:
                continue

            student = None
            if email_col:
                student_result = await self.db.execute(
                    select(User).where(
                        User.email == lookup_value,
                        User.institution_id == institution_id,
                        User.role == UserRole.STUDENT,
                    )
                )
                student = student_result.scalar_one_or_none()
            elif roll_col:
                student_result = await self.db.execute(
                    select(User).where(
                        User.roll_number == lookup_value,
                        User.institution_id == institution_id,
                        User.role == UserRole.STUDENT,
                    )
                )
                student = student_result.scalar_one_or_none()

            if not student:
                not_found.append(lookup_value)
                continue

            if student.id in already_enrolled:
                skipped_count += 1
                continue

            self.db.add(Enrollment(student_id=student.id, course_id=course_id))
            already_enrolled.add(student.id)
            enrolled_count += 1

        await self.db.commit()
        return {
            "enrolled_count": enrolled_count,
            "skipped_count": skipped_count,
            "not_found": not_found,
        }

    async def bulk_enroll_from_ids(
        self, course_id: UUID, student_ids: list[UUID]
    ) -> dict:
        result = await self.db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        if not course:
            raise LookupError("Course not found")

        existing_q = select(Enrollment.student_id).where(
            Enrollment.course_id == course_id,
            Enrollment.student_id.in_(student_ids),
        )
        existing_result = await self.db.execute(existing_q)
        already_enrolled = {row[0] for row in existing_result.all()}

        enrolled = 0
        skipped = 0
        for student_id in student_ids:
            if student_id in already_enrolled:
                skipped += 1
                continue
            self.db.add(Enrollment(student_id=student_id, course_id=course_id))
            enrolled += 1

        await self.db.commit()
        return {"enrolled": enrolled, "skipped": skipped}
