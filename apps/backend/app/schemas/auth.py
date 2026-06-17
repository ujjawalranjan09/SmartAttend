from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    totp_code: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: UserRole
    user_id: str


class TOTPSetupResponse(BaseModel):
    secret: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=200)
    role: UserRole = UserRole.STUDENT
    institution_id: UUID


class VerifyRegistrationRequest(BaseModel):
    token: str


class UserRegistrationResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: UserRole
