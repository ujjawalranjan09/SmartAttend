import logging
import uuid
from datetime import datetime

import structlog
from sqlalchemy import event, insert

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)

_SENSITIVE_FIELDS = frozenset({"hashed_password", "embedding", "totp_secret"})

AUDITED_MODELS = frozenset(
    {
        "User",
        "ClassSession",
        "AttendanceRecord",
        "Course",
        "Enrollment",
    }
)


def _obj_to_dict(obj) -> dict:
    """Serialize an ORM instance to a dict using DB column names as keys.

    The Python attribute name on the model class can differ from the DB column
    name when ``mapped_column("db_name", ...)`` is used with a different
    left-hand-side (``date: Mapped[...] = mapped_column("scheduled_at", ...)``).
    Build a ``db_column_name -> python_attr_name`` map from ``column_attrs`` so
    ``getattr`` works regardless of how the model declared the column.
    """
    col_to_attr = {}
    for py_name, prop in obj.__mapper__.column_attrs.items():
        for c in prop.columns:
            col_to_attr.setdefault(c.name, py_name)
    result = {}
    for col in obj.__table__.columns:
        if col.name in _SENSITIVE_FIELDS:
            continue
        py_name = col_to_attr.get(col.name, col.name)
        value = getattr(obj, py_name)
        if isinstance(value, uuid.UUID):
            value = str(value)
        elif isinstance(value, datetime):
            value = value.isoformat()
        elif hasattr(value, "value"):
            value = value.value
        result[col.name] = value
    return result


def _get_user_id(obj) -> uuid.UUID | None:
    for attr in ("user_id", "student_id", "faculty_id"):
        uid = getattr(obj, attr, None)
        if uid is not None:
            return uid
    return None


def _get_request_context() -> dict:
    """Read IP and user-agent from structlog context vars (set by middleware)."""
    ctx = structlog.contextvars.get_contextvars()
    return {
        "ip_address": ctx.get("client_ip"),
        "user_agent": ctx.get("user_agent"),
    }


def _after_insert(mapper, connection, target):
    resource_type = target.__class__.__name__
    if resource_type not in AUDITED_MODELS:
        return
    try:
        resource_id = getattr(target, "id", None)
        if resource_id is not None:
            resource_id = str(resource_id)
        req_ctx = _get_request_context()
        connection.execute(
            insert(AuditLog).values(
                user_id=_get_user_id(target),
                action=f"{resource_type}.create",
                resource_type=resource_type,
                resource_id=resource_id,
                new_value=_obj_to_dict(target),
                ip_address=req_ctx.get("ip_address"),
                user_agent=req_ctx.get("user_agent"),
            )
        )
    except Exception:
        logger.exception("Failed to capture audit log for %s", target)


def _after_update(mapper, connection, target):
    resource_type = target.__class__.__name__
    if resource_type not in AUDITED_MODELS:
        return
    try:
        resource_id = getattr(target, "id", None)
        if resource_id is not None:
            resource_id = str(resource_id)
        req_ctx = _get_request_context()
        connection.execute(
            insert(AuditLog).values(
                user_id=_get_user_id(target),
                action=f"{resource_type}.update",
                resource_type=resource_type,
                resource_id=resource_id,
                new_value=_obj_to_dict(target),
                ip_address=req_ctx.get("ip_address"),
                user_agent=req_ctx.get("user_agent"),
            )
        )
    except Exception:
        logger.exception("Failed to capture audit log for %s", target)


def setup_audit_listeners():
    from app.models.user import User
    from app.models.session import ClassSession
    from app.models.attendance import AttendanceRecord
    from app.models.course import Course, Enrollment

    target_models = [User, ClassSession, AttendanceRecord, Course, Enrollment]
    for model_cls in target_models:
        event.listen(model_cls, "after_insert", _after_insert, propagate=True)
        event.listen(model_cls, "after_update", _after_update, propagate=True)

    logger.info("Audit event listeners registered")
