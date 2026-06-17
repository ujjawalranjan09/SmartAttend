from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User, UserRole
from app.models.face import FaceEmbedding
from app.services.face_service import FaceService
from app.services.image_optimizer import optimize_image
from app.schemas.face import FaceEnrollmentResponse
from sqlalchemy import select

router = APIRouter(tags=["Face Enrollment"])


@router.post("/enroll", response_model=FaceEnrollmentResponse)
async def enroll_face(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Enroll the current user's face by uploading an image.
    Image is optimized (resized, compressed, EXIF stripped) before processing.
    """
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can enroll face",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image file",
        )

    # Optimize image (resize to max 640x640, compress, strip EXIF)
    try:
        optimized_bytes = optimize_image(image_bytes)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    # Extract embedding via ML service (now gets optimized image)
    face_svc = FaceService(db)
    embedding = await face_svc.extract_embedding_from_image(optimized_bytes)

    if embedding is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Face embedding service unavailable. Please try again later.",
        )

    # Store the embedding
    record = await face_svc.enroll_face(current_user.id, embedding)
    return FaceEnrollmentResponse(
        enrolled=True,
        enrolled_at=record.enrolled_at,
        model_version=record.model_version,
    )


@router.get("/status", response_model=FaceEnrollmentResponse)
async def face_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if the current user has a face enrollment."""
    face_svc = FaceService(db)
    enrolled = await face_svc.has_enrollment(current_user.id)

    result = await db.execute(
        select(FaceEmbedding).where(
            FaceEmbedding.user_id == current_user.id,
            FaceEmbedding.is_active == True,
        )
    )
    record = result.scalar_one_or_none()

    return FaceEnrollmentResponse(
        enrolled=enrolled,
        enrolled_at=record.enrolled_at if record else None,
        model_version=record.model_version if record else None,
    )


@router.delete("/enrollment", status_code=status.HTTP_204_NO_CONTENT)
async def delete_enrollment(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove face enrollment for the current user."""
    result = await db.execute(
        select(FaceEmbedding).where(
            FaceEmbedding.user_id == current_user.id,
        )
    )
    record = result.scalar_one_or_none()

    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No face enrollment found",
        )

    record.is_active = False
    await db.commit()