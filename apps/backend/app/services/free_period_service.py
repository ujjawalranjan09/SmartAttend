"""
FreePeriodService — detects gaps in a student's daily schedule.
No external API calls, purely logic-based.
"""

import uuid
from datetime import date, time
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Enrollment
from app.models.session import TimetableSlot


class FreePeriodService:
    # Campus day boundaries (can be overridden via __init__)
    CAMPUS_START = time(8, 0)
    CAMPUS_END = time(18, 0)
    # Minimum gap to qualify as a free period (strictly greater than this value)
    MIN_GAP_MINUTES = 30

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def detect_free_periods(
        self, student_id: UUID, target_date: date
    ) -> list[dict]:
        """
        Detect free periods for a student on a given date.

        Returns a list of dicts:
          { start_time: "HH:MM", end_time: "HH:MM", duration_minutes: int }
        Only gaps >= 30 minutes within the campus day are returned.
        """
        # 1. Get the student's enrolled course IDs
        enroll_result = await self.db.execute(
            select(Enrollment.course_id).where(Enrollment.student_id == student_id)
        )
        course_ids = [r for r in enroll_result.scalars().all()]
        if not course_ids:
            return self._gaps_from_slots([], target_date)

        # 2. Get timetable slots for those courses on the target day
        weekday = target_date.weekday()  # 0=Mon, 6=Sun
        slots_result = await self.db.execute(
            select(TimetableSlot)
            .where(
                and_(
                    TimetableSlot.course_id.in_(course_ids),
                    TimetableSlot.day_of_week == weekday,
                )
            )
            .order_by(TimetableSlot.start_time)
        )
        slots = list(slots_result.scalars().all())

        return self._gaps_from_slots(slots, target_date)

    def _gaps_from_slots(
        self, slots: list[TimetableSlot], target_date: date
    ) -> list[dict]:
        """
        Given a list of sorted timetable slots for a day, compute free periods.
        campus_start=08:00, campus_end=18:00, min_gap=30 minutes.
        """
        result: list[dict] = []

        # Helper to convert time to minutes-since-midnight
        def to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute

        start_of_day = to_minutes(self.CAMPUS_START)
        end_of_day = to_minutes(self.CAMPUS_END)

        # Build sorted (start_minutes, end_minutes) pairs
        occupied = sorted(
            [(to_minutes(s.start_time), to_minutes(s.end_time)) for s in slots]
        )

        cursor = start_of_day

        for occ_start, occ_end in occupied:
            # Gap between cursor and this class
            if occ_start - cursor > self.MIN_GAP_MINUTES:
                result.append(
                    {
                        "start_time": self._minutes_to_str(cursor),
                        "end_time": self._minutes_to_str(occ_start),
                        "duration_minutes": occ_start - cursor,
                    }
                )
            # Advance cursor past this class
            cursor = max(cursor, occ_end)

        # Final gap after last class
        if end_of_day - cursor > self.MIN_GAP_MINUTES:
            result.append(
                {
                    "start_time": self._minutes_to_str(cursor),
                    "end_time": self._minutes_to_str(end_of_day),
                    "duration_minutes": end_of_day - cursor,
                }
            )

        return result

    async def get_free_periods_for_week(
        self, student_id: UUID, week_start: date
    ) -> dict[str, list[dict]]:
        """
        Return free periods for Mon-Fri starting from week_start.
        Returns dict keyed by "YYYY-MM-DD".
        """
        from datetime import timedelta

        result = {}
        current = week_start
        for _ in range(5):  # Mon to Fri
            result[current.isoformat()] = await self.detect_free_periods(
                student_id, current
            )
            current += timedelta(days=1)
        return result

    @staticmethod
    def _minutes_to_str(minutes: int) -> str:
        h, m = divmod(minutes, 60)
        return f"{h:02d}:{m:02d}"