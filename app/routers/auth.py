# routers/auth.py
# Stage 5 change: register now calls register_user_job() so new users
# start getting automated scrapes immediately without a server restart.

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_async_session, User, UserSettings
from app.schemas import UserCreate, UserResponse, TokenResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.scheduler import register_user_job

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserCreate,
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.email == body.email))
    if result.scalars().first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with that email already exists"
        )

    user = User(email=body.email, password=hash_password(body.password))
    session.add(user)
    await session.flush()   # populate user.id before creating settings

    settings = UserSettings(
        user_id              = user.id,
        email_enabled        = False,
        alert_threshold      = 5.0,
        check_interval_hours = 6.0,
        search_queries       = "3090,3080,4090",
    )
    session.add(settings)
    await session.commit()
    await session.refresh(user)

    # Register scheduler job immediately — no restart needed
    register_user_job(user.id, settings.check_interval_hours)

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    result = await session.execute(select(User).where(User.email == form.username))
    user = result.scalars().first()

    if not user or not verify_password(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {"access_token": create_access_token(user_id=user.id), "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
