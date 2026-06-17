from uuid import UUID
from datetime import date, datetime, time, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import TimetableSlot, ClassSession, SessionStatus
from app.models.course import Course
from app.schemas.timetable import SlotCreate, SlotUpdate


DAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


class TimetableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_slot(self, data: SlotCreate) -> TimetableSlot:
        slot = TimetableSlot(
            course_id=data.course_id,
            day_of_week=data.day_of_week,
            start_time=data.start_time,
            end_time=data.end_time,
            room=data.room,
            building=data.building,
            geo_lat=data.geo_lat,
            geo_lon=data.geo_lon,
            geo_radius_m=data.geo_radius_m,
        )
        self.db.add(slot)
        await self.db.flush()
        await self.db.refresh(slot)
        return slot

    async def list_slots(
        self, course_id: UUID | None = None, department_id: UUID | None = None
    ) -> list[TimetableSlot]:
        q = select(TimetableSlot)
        if course_id:
            q = q.where(TimetableSlot.course_id == course_id)
        if department_id:
            q = q.join(Course, TimetableSlot.course_id == Course.id).where(
                Course.department_id == department_id
            )
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def update_slot(
        self, slot_id: UUID, data: SlotUpdate
    ) -> TimetableSlot | None:
        result = await self.db.execute(
            select(TimetableSlot).where(TimetableSlot.id == slot_id)
        )
        slot = result.scalar_one_or_none()
        if not slot:
            return None
        update_data = data.model_dump(exclude_none=True)
        for field, value in update_data.items():
            setattr(slot, field, value)
        await self.db.flush()
        await self.db.refresh(slot)
        return slot

    async def delete_slot(self, slot_id: UUID) -> bool:
        result = await self.db.execute(
            select(TimetableSlot).where(TimetableSlot.id == slot_id)
        )
        slot = result.scalar_one_or_none()
        if not slot:
            return False
        await self.db.delete(slot)
        await self.db.flush()
        return True

    async def generate_sessions_for_week(
        self, start_date: date, institution_id: UUID | None = None
    ) -> int:
        week_end = start_date + timedelta(days=6)
        q = select(TimetableSlot)
        if institution_id:
            q = q.join(Course, TimetableSlot.course_id == Course.id).where(
                Course.institution_id == institution_id
            )
        result = await self.db.execute(q)
        slots = list(result.scalars().all())

        count = 0
        for slot in slots:
            target_date = start_date + timedelta(days=slot.day_of_week)
            if target_date > week_end:
                continue

            existing = await self.db.execute(
                select(ClassSession).where(
                    and_(
                        ClassSession.timetable_slot_id == slot.id,
                        ClassSession.date >= datetime.combine(target_date, time.min),
                        ClassSession.date
                        < datetime.combine(target_date + timedelta(days=1), time.min),
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            course = await self.db.get(Course, slot.course_id)
            if not course:
                continue
            faculty_id = course.faculty_id

            session = ClassSession(
                course_id=slot.course_id,
                timetable_slot_id=slot.id,
                faculty_id=faculty_id,
                date=datetime.combine(target_date, slot.start_time),
                status=SessionStatus.SCHEDULED,
            )
            self.db.add(session)
            count += 1

        await self.db.flush()
        return count

    async def get_weekly_view(self, institution_id: UUID, week_start: date) -> dict:
        week_end = week_start + timedelta(days=6)

        result = await self.db.execute(
            select(ClassSession)
            .join(Course, ClassSession.course_id == Course.id)
            .where(
                and_(
                    Course.institution_id == institution_id,
                    ClassSession.date >= datetime.combine(week_start, time.min),
                    ClassSession.date <= datetime.combine(week_end, time.max),
                )
            )
        )
        sessions = list(result.scalars().all())

        # Batch-load courses and slots to avoid N+1 queries
        course_ids = {s.course_id for s in sessions}
        slot_ids = {s.timetable_slot_id for s in sessions if s.timetable_slot_id}

        courses_map = {}
        if course_ids:
            course_result = await self.db.execute(
                select(Course).where(Course.id.in_(course_ids))
            )
            courses_map = {c.id: c for c in course_result.scalars().all()}

        slots_map = {}
        if slot_ids:
            slot_result = await self.db.execute(
                select(TimetableSlot).where(TimetableSlot.id.in_(slot_ids))
            )
            slots_map = {s.id: s for s in slot_result.scalars().all()}

        sessions_by_day: dict[int, list] = {i: [] for i in range(7)}
        for s in sessions:
            day_idx = s.date.weekday()
            course = courses_map.get(s.course_id)
            slot_info = {}
            if s.timetable_slot_id:
                slot = slots_map.get(s.timetable_slot_id)
                if slot:
                    slot_info = {"room": slot.room, "building": slot.building}

            sessions_by_day[day_idx].append(
                {
                    "session_id": str(s.id),
                    "course_id": str(s.course_id),
                    "course_name": course.name if course else None,
                    "date": s.date.isoformat(),
                    "status": s.status.value if s.status else None,
                    "room": slot_info.get("room"),
                    "building": slot_info.get("building"),
                }
            )

        days = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            days.append(
                {
                    "date": d.isoformat(),
                    "day_name": DAY_NAMES[i],
                    "slots": sessions_by_day[i],
                }
            )

        return {"days": days}
