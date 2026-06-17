"""
Locust load testing script for SmartAttend API.
Tests login, session listing, attendance marking, and analytics.
"""
from locust import HttpUser, task, between, constant


class SmartAttendUser(HttpUser):
    """Simulates a student user performing common actions."""
    wait_time = between(1, 3)

    def on_start(self):
        """Login on start and store token."""
        self.token = None
        self.session_id = None

        # Try to login with a test student account
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "student@test.edu", "password": "student123"},
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_sessions(self):
        """List available sessions."""
        if self.token:
            self.client.get("/api/v1/sessions?limit=10", headers=self.headers)

    @task(5)
    def mark_attendance(self):
        """Mark attendance for a session."""
        if self.token:
            # Get active sessions first
            resp = self.client.get(
                "/api/v1/sessions?status=active&limit=1", headers=self.headers
            )
            if resp.status_code == 200 and resp.json().get("items"):
                session = resp.json()["items"][0]
                self.client.post(
                    "/api/v1/attendance/mark",
                    headers=self.headers,
                    json={
                        "session_id": session["id"],
                        "qr_token": session.get("qr_token", "test-token"),
                        "lat": 28.6139 + (self.environment.runner.user_count * 0.0001),
                        "lon": 77.2090,
                    },
                )

    @task(2)
    def view_analytics(self):
        """View analytics dashboard."""
        if self.token:
            self.client.get("/api/v1/analytics/student/me", headers=self.headers)

    @task(1)
    def check_alerts(self):
        """Check unresolved alerts."""
        if self.token:
            self.client.get(
                "/api/v1/alerts?is_resolved=false&limit=5", headers=self.headers
            )

    @task(1)
    def list_notifications(self):
        """List notifications."""
        if self.token:
            self.client.get(
                "/api/v1/notifications?limit=10", headers=self.headers
            )


class FacultyUser(HttpUser):
    """Simulates a faculty member managing sessions."""
    wait_time = constant(2)

    def on_start(self):
        resp = self.client.post(
            "/api/v1/auth/login",
            json={"email": "faculty@test.edu", "password": "faculty123"},
        )
        if resp.status_code == 200:
            data = resp.json()
            self.token = data["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

    @task(3)
    def list_attendance(self):
        """View attendance records."""
        if self.token:
            self.client.get(
                "/api/v1/attendance?limit=50", headers=self.headers
            )

    @task(2)
    def list_alerts(self):
        """View institution alerts."""
        if self.token:
            self.client.get(
                "/api/v1/alerts?is_resolved=false&limit=20", headers=self.headers
            )

    @task(1)
    def view_course_analytics(self):
        """View course analytics."""
        if self.token:
            self.client.get("/api/v1/analytics/summary", headers=self.headers)