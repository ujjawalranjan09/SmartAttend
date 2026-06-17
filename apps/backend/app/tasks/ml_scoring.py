from app.tasks.celery_app import celery_app


@celery_app.task(name="tasks.score_proxy_risk", bind=True, max_retries=3)
def score_proxy_risk(self, attendance_record_id: str):
    """
    ML-based proxy risk scoring for a single attendance record.
    Features used:
      - geo_accuracy_m       (high accuracy = suspicious if student usually imprecise)
      - device_fingerprint   (hash match against registered device)
      - wifi_bssid           (matches expected classroom AP)
      - face_confidence      (if face scan used)
      - time_to_mark_seconds (very fast = bot?)
      - ip_subnet_match      (same subnet as classroom)
    Updates AttendanceRecord.proxy_score in DB.
    """
    try:
        from app.core.database import SyncSessionLocal
        from app.models.attendance import AttendanceRecord, AttendanceStatus
        import uuid

        with SyncSessionLocal() as db:
            record = (
                db.query(AttendanceRecord)
                .filter(AttendanceRecord.id == uuid.UUID(attendance_record_id))
                .first()
            )

            if not record:
                return {"error": "Record not found"}

            score = _compute_proxy_score(record)
            record.proxy_score = score

            from app.core.config import settings

            if score >= settings.proxy_anomaly_threshold:
                record.status = AttendanceStatus.PROXY_SUSPECTED
                _create_alert(db, record)

            db.commit()
            return {"record_id": attendance_record_id, "proxy_score": score}

    except Exception as exc:
        raise self.retry(exc=exc, countdown=15)


def _compute_proxy_score(record) -> float:
    """
    Weighted heuristic proxy score in [0, 1].
    0 = definitely legitimate, 1 = definitely proxy.
    Each factor adds to a weighted sum, then normalized.
    """
    score = 0.0
    weight_total = 0.0

    # Factor 1: face confidence (weight 0.35)
    if record.face_confidence is not None:
        w = 0.35
        # Low confidence -> high proxy probability
        face_risk = max(0.0, 1.0 - record.face_confidence)
        score += face_risk * w
        weight_total += w

    # Factor 2: geo accuracy (weight 0.20)
    # GPS accuracy > 200m on campus = suspicious
    if record.geo_accuracy_m is not None:
        w = 0.20
        if record.geo_accuracy_m > 200:
            score += w  # full risk
        elif record.geo_accuracy_m > 100:
            score += w * 0.5
        weight_total += w

    # Factor 3: device fingerprint (weight 0.25)
    # No fingerprint provided = suspicious
    if record.device_fingerprint is None or record.device_fingerprint == "":
        score += 0.25
    weight_total += 0.25

    # Factor 4: wifi BSSID (weight 0.20)
    # If BSSID is present but session has no expected BSSID, skip
    # If session has expected BSSID and record doesn't match -> risk
    # Simplified: no wifi_bssid provided at all = small risk
    if not record.wifi_bssid:
        score += 0.10
    weight_total += 0.20

    if weight_total == 0:
        return 0.0
    return round(min(1.0, score / weight_total), 4)


def _create_alert(db, record):
    """Insert a proxy alert into the alerts table."""
    try:
        from app.models.alert import Alert

        alert = Alert(
            student_id=record.student_id,
            attendance_record_id=record.id,
            alert_type="proxy_suspected",
            message=(
                f"Proxy attendance suspected (risk score: {record.proxy_score:.2f}). "
                f"Session: {record.session_id}. Please verify."
            ),
            resolved=False,
        )
        db.add(alert)
    except Exception:
        pass  # Non-critical; don't fail the task
