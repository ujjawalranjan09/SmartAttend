from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, delete
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == str(user_id))
        )
        return result.scalar_one_or_none()

    async def get_by_roll(self, roll_number: str, institution_id: UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(
                User.roll_number == roll_number,
                User.institution_id == institution_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        institution_id: UUID,
        role: Optional[UserRole] = None,
        department_id: Optional[UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[User], int]:
        q = select(User).where(User.institution_id == institution_id)
        if role:
            q = q.where(User.role == role)
        if department_id:
            q = q.where(User.department_id == department_id)
        if is_active is not None:
            q = q.where(User.is_active == is_active)
        if search:
            like = f"%{search}%"
            q = q.where(
                User.full_name.ilike(like) | User.email.ilike(like) | User.roll_number.ilike(like)
            )

        count_q = select(func.count()).select_from(q.subquery())
        total_result = await self.db.execute(count_q)
        total = total_result.scalar() or 0

        q = q.order_by(User.full_name).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(q)
        return result.scalars().all(), total

    # ── Write ─────────────────────────────────────────────────────────────

    async def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            phone=data.phone,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=data.role,
            institution_id=data.institution_id,
            department_id=data.department_id,
            roll_number=data.roll_number,
            employee_id=data.employee_id,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: UUID, data: UserUpdate) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(user, field, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def deactivate(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            update(User).where(User.id == str(user_id)).values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def hard_delete(self, user_id: UUID) -> bool:
        result = await self.db.execute(
            delete(User).where(User.id == str(user_id))
        )
        await self.db.commit()
        return result.rowcount > 0

    async def bulk_create(self, users_data: list[UserCreate]) -> dict:
        created, failed, errors = 0, 0, []
        for data in users_data:
            try:
                await self.create(data)
                created += 1
            except IntegrityError as e:
                await self.db.rollback()
                failed += 1
                errors.append({"email": data.email, "error": str(e.orig)})
            except Exception as e:
                await self.db.rollback()
                failed += 1
                errors.append({"email": data.email, "error": str(e)})
        return {"created": created, "failed": failed, "errors": errors}

    async def enable_totp(self, user_id: UUID, secret: str) -> bool:
        result = await self.db.execute(
            update(User)
            .where(User.id == str(user_id))
            .values(totp_secret=secret, totp_enabled=True)
        )
        await self.db.commit()
        return result.rowcount > 0
