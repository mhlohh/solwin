from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.schemas.auth import CurrentUserResponse, LoginRequest, TokenResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate user and return access token",
    description=(
        "Authenticates user credentials using email and password. "
        "Returns a signed JWT access token on success. "
        "Does not disclose whether the email address exists."
    ),
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
        token_response = AuthService.login(
            db=db,
            email=payload.email,
            password=payload.password,
        )
        return token_response
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user profile",
    description=(
        "Returns the profile and role details of the currently " "authenticated user."
    ),
)
def get_me(
    current_user: User = Depends(get_current_active_user),
):
    return current_user
