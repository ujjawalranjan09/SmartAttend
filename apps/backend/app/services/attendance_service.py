from uuid import UUID
from math import radians, sin, cos, sqrt, atan2
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.attendance import AttendanceRecord, AttendanceMethod, AttendanceStatus
from app.models.session import ClassSession
from app.models.institution import Institution
from app.models.course import Course


class AttendanceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def validate_geofence(
        self,
        session_id: UUID,
        lat: float | None,
        lon: float | None,
    ) -> bool:
        """Check if student's GPS is within the classroom geo-fence radius."""
        if lat is None or lon is None:
            return True  # Skip if GPS not available (QR-only mode)

        result = await self.db.execute(
            select(ClassSession).where(ClassSession.id == session_id)
        )
        session = result.scalar_one_or_none()
        if not session:
            return False

        # Get geo-fence config (from timetable slot or institution default)
        slot = session.timetable_slot
        geo_lat = slot.geo_lat if slot and slot.geo_lat else None
        geo_lon = slot.geo_lon if slot and slot.geo_lon else None
        radius_m = slot.geo_radius_m if slot and slot.geo_radius_m else 150

        if geo_lat is None:
            return True  # No fence configured

        distance = self._haversine_distance(lat, lon, geo_lat, geo_lon)
        return distance <= radius_m

    def _haversine_distance(
        self, lat1: float, lon1: float, lat2: float, lon2: float
    ) -> float:
        """Calculate distance in meters between two GPS coordinates."""
        R = 6371000  # Earth radius in meters
        phi1, phi2 = radians(lat1), radians(lat2)
        dphi = radians(lat2 - lat1)
        dlambda = radians(lon2 - lon1)
        a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
        return R * 2 * atan2(sqrt(a), sqrt(1 - a))

    async def _get_attendance_pct(self, student_id: UUID, session_id: UUID) -> float:
        result = await self.db.execute(
            select(ClassSession.course_id).where(ClassSession.id == session_id)
        )
        course_id = result.scalar_one()
        result = await self.db.execute(
            select(AttendanceRecord)
            .join(ClassSession, AttendanceRecord.session_id == ClassSession.id)
            .where(
                AttendanceRecord.student_id == student_id,
                ClassSession.course_id == course_id,
            )
        )
        records = result.scalars().all()
        total = len(records)
        if total == 0:
            return 100.0
        present = sum(1 for r in records if r.status == AttendanceStatus.PRESENT)
        return (present / total) * 100

    async def create_record(self, **kwargs) -> AttendanceRecord:
        face_embedding = kwargs.pop("face_embedding", None)
        record = AttendanceRecord(**kwargs)
        self.db.add(record)
        await self.db.flush()

        # If face embedding provided, do similarity check via ML service
        if face_embedding:
            from app.services.face_service import FaceService

            face_svc = FaceService(self.db)

            # Check if student has face enrollment first
            has_enrollment = await face_svc.has_enrollment(kwargs["student_id"])

            if not has_enrollment:
                # No enrollment — skip face verification, note it
                record.face_confidence = 0.0
                record.verification_notes = "Face not enrolled — verification skipped"
            else:
                confidence = await face_svc.verify_embedding(
                    student_id=kwargs["student_id"],
                    embedding=face_embedding,
                )
                record.face_confidence = confidence

                if confidence < 0.5:  # Too low — flag for review
                    record.status = AttendanceStatus.PROXY_SUSPECTED
                elif confidence < 0.7:  # Low confidence but above proxy threshold
                    record.verification_notes = "Low face confidence — review recommended"
                    # Keep status as PRESENT but note it
                    if record.status != AttendanceStatus.PROXY_SUSPECTED:
                        record.status = AttendanceStatus.PRESENT
                else:
                    record.verification_notes = "Face verified"

        await self.db.commit()

        pct = await self._get_attendance_pct(record.student_id, record.session_id)
        if pct < 75:
            from app.tasks.notifications import send_low_attendance_alert

            result = await self.db.execute(
                select(Course.name)
                .join(ClassSession, Course.id == ClassSession.course_id)
                .where(ClassSession.id == record.session_id)
            )
            course_name = result.scalar()
            send_low_attendance_alert.delay(str(record.student_id), course_name, pct)

        return record

    async def get_by_session(self, session_id: UUID) -> list[AttendanceRecord]:
        result = await self.db.execute(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session_id)
        )
        return result.scalars().all()

    async def override_status(
        self, record_id: UUID, new_status: str, notes: str
    ) -> AttendanceRecord:
        result = await self.db.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == record_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise ValueError("Record not found")
        record.status = new_status
        record.method = AttendanceMethod.MANUAL_OVERRIDE
        record.verification_notes = notes
        record.is_verified = True
        await self.db.commit()
        return record