#!/usr/bin/env python3
"""
Seed realistic analytics data for testing.

Run inside the api container:
  PYTHONPATH=/app python scripts/seed_analytics_data.py
"""
import uuid
import random
from datetime import datetime, timedelta
import psycopg2
from psycopg2.extras import execute_values

# Demo credentials from seed
DEMO_FACULTY_EMAIL = "faculty@smartattend.in"
DEMO_COURSE_CODE = "IT401"

def main():
    conn = psycopg2.connect(
        host="db",
        dbname="smartattend",
        user="smartattend",
        password="smartattend_secret"
    )
    cur = conn.cursor()

    # 1. Find key IDs
    cur.execute("SELECT id FROM users WHERE email = %s", (DEMO_FACULTY_EMAIL,))
    faculty = cur.fetchone()
    if not faculty:
        print("Faculty not found. Run seed_demo.py first.")
        return
    faculty_id = faculty[0]

    cur.execute("SELECT id FROM courses WHERE code = %s", (DEMO_COURSE_CODE,))
    course = cur.fetchone()
    if not course:
        print("Course IT401 not found.")
        return
    course_id = course[0]

    cur.execute("""
        SELECT id FROM users 
        WHERE role = 'student' AND institution_id = (
            SELECT institution_id FROM users WHERE email = %s
        )
        ORDER BY created_at
        LIMIT 5
    """, (DEMO_FACULTY_EMAIL,))
    students = [row[0] for row in cur.fetchall()]

    print(f"Faculty: {faculty_id}")
    print(f"Course:  {course_id}")
    print(f"Students: {len(students)}")

    # 2. Clean old demo sessions + attendance for this course
    cur.execute("""
        DELETE FROM attendance_records 
        WHERE session_id IN (
            SELECT id FROM class_sessions WHERE course_id = %s
        )
    """, (course_id,))
    cur.execute("DELETE FROM class_sessions WHERE course_id = %s", (course_id,))
    print("Cleaned old demo sessions/attendance.")

    # 3. Create 10 sessions over the last ~3 weeks
    now = datetime.utcnow()
    sessions_to_create = []

    for i in range(10):
        days_ago = 21 - (i * 2) + random.randint(-1, 1)
        session_date = now - timedelta(days=days_ago)
        started = session_date + timedelta(hours=9, minutes=random.randint(0, 10))
        
        status = "completed" if i < 9 else "active"
        ended = started + timedelta(hours=1, minutes=30) if status == "completed" else None

        sessions_to_create.append((
            str(uuid.uuid4()),
            str(course_id),
            str(faculty_id),
            None,  # timetable_slot_id
            started,  # scheduled_at
            started,
            ended,
            status,
            None,  # qr_token
            "IT-Lab-3",
            now
        ))

    execute_values(cur, """
        INSERT INTO class_sessions 
        (id, course_id, faculty_id, timetable_slot_id, scheduled_at, started_at, ended_at, status, qr_token, room, created_at)
        VALUES %s
    """, sessions_to_create)

    print(f"Created {len(sessions_to_create)} sessions.")

    # Get the session IDs we just created
    cur.execute("SELECT id FROM class_sessions WHERE course_id = %s ORDER BY started_at", (course_id,))
    session_ids = [row[0] for row in cur.fetchall()]

    # 4. Create realistic attendance records
    attendance_rows = []
    methods = ["qr_code", "qr_code", "qr_code", "face_recognition", "manual_override"]

    for sess_id in session_ids:
        is_recent = sess_id == session_ids[-1]  # last one is active

        for stud_id in students:
            # Realistic distribution: ~78% present on average
            roll = random.random()
            if roll < 0.78:
                status = "present"
                method = random.choice(methods)
                face_conf = round(random.uniform(0.82, 0.97), 2) if method == "face_recognition" else None
                proxy = None
            elif roll < 0.90:
                status = "absent"
                method = "qr_code"
                face_conf = None
                proxy = None
            else:
                status = "proxy_suspected"
                method = random.choice(["qr_code", "face_recognition"])
                face_conf = round(random.uniform(0.35, 0.55), 2) if method == "face_recognition" else None
                proxy = round(random.uniform(0.65, 0.92), 2)

            marked = (now - timedelta(days=random.randint(0, 20), hours=random.randint(0, 3))) if not is_recent else now - timedelta(hours=1)

            attendance_rows.append((
                str(uuid.uuid4()),
                str(sess_id),
                str(stud_id),
                status,
                method,
                marked,
                None, None, None,  # geo
                "demo-device-" + str(random.randint(1000,9999)),
                "AA:BB:CC:DD:EE:FF",
                face_conf,
                proxy,
                "127.0.0.1",
                "SmartAttend/1.0",
                False,
                None,
                now
            ))

    if attendance_rows:
        execute_values(cur, """
            INSERT INTO attendance_records 
            (id, session_id, student_id, status, method, marked_at, 
             geo_lat, geo_lon, geo_accuracy_m, device_fingerprint, wifi_bssid,
             face_confidence, proxy_score, ip_address, user_agent, 
             is_verified, verification_notes, created_at)
            VALUES %s
        """, attendance_rows)

        print(f"Created {len(attendance_rows)} attendance records.")

    conn.commit()
    cur.close()
    conn.close()

    print("\n✅ Analytics seed data inserted successfully!")
    print("   - 10 class sessions (9 completed + 1 active)")
    print("   - ~40-50 attendance records with realistic distribution")
    print("   - Mix of present / absent / proxy_suspected")
    print("\nYou can now test the Analytics section as faculty.")


if __name__ == "__main__":
    main()
