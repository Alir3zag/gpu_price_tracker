# ============================================================
# routers/settings.py — GET and PATCH /settings
# Requires a valid JWT — every endpoint uses get_current_user
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_async_session, User, UserSettings
from app.schemas import UserSettingsUpdate, UserSettingsResponse
from app.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_or_create_settings(user: User, session: AsyncSession) -> UserSettings:
    """Return the UserSettings row for this user, creating defaults if missing.

    We call this on every request so we never have to worry about
    whether settings exist — they always will after the first touch.
    """
    result = await session.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = result.scalars().first()

    if settings is None:
        # First time this user hits /settings — create a row with sensible defaults
        settings = UserSettings(user_id=user.id)
        session.add(settings)
        await session.commit()
        await session.refresh(settings)

    return settings


# ── GET /settings ─────────────────────────────────────────────────────────────

@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Return the current user's settings.

    search_queries is stored as a comma-separated string in the DB
    ("3090,3080,4090") and returned as a proper list (["3090","3080","4090"])
    so the API consumer never has to know about the internal storage format.
    """
    settings = await _get_or_create_settings(current_user, session)

    return UserSettingsResponse(
        email_enabled        = settings.email_enabled,
        alert_threshold      = settings.alert_threshold,
        check_interval_hours = settings.check_interval_hours,
        # split on comma and strip whitespace so "3090, 3080" → ["3090", "3080"]
        search_queries       = [q.strip() for q in settings.search_queries.split(",") if q.strip()],
    )


# ── PATCH /settings ───────────────────────────────────────────────────────────

@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    body: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    """Update one or more settings fields. Only provided fields are changed.

    We use PATCH (not PUT) because the client can send a partial body —
    e.g. just {"alert_threshold": 10.0} without touching email_enabled.

    Validation rules:
    - alert_threshold must be between 1% and 90%
    - check_interval_hours must be between 0.5h and 168h (1 week)
    - search_queries can't be empty
    """
    settings = await _get_or_create_settings(current_user, session)

    # --- validate before touching anything ---
    if body.alert_threshold is not None:
        if not (1.0 <= body.alert_threshold <= 90.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="alert_threshold must be between 1 and 90 (percent)"
            )

    if body.check_interval_hours is not None:
        if not (0.5 <= body.check_interval_hours <= 168.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="check_interval_hours must be between 0.5 and 168"
            )

    if body.search_queries is not None:
        cleaned = [q.strip() for q in body.search_queries if q.strip()]
        if not cleaned:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="search_queries must contain at least one query"
            )

    # --- apply only the fields the client actually sent ---
    # body.model_fields_set contains only the keys present in the request JSON,
    # so PATCH {"email_enabled": true} won't zero out alert_threshold.
    if "email_enabled" in body.model_fields_set:
        settings.email_enabled = body.email_enabled

    if "alert_threshold" in body.model_fields_set:
        settings.alert_threshold = body.alert_threshold

    if "check_interval_hours" in body.model_fields_set:
        settings.check_interval_hours = body.check_interval_hours

    if "search_queries" in body.model_fields_set:
        cleaned = [q.strip() for q in body.search_queries if q.strip()]
        settings.search_queries = ",".join(cleaned)     # store as "3090,3080,4090"

    await session.commit()
    await session.refresh(settings)

    return UserSettingsResponse(
        email_enabled        = settings.email_enabled,
        alert_threshold      = settings.alert_threshold,
        check_interval_hours = settings.check_interval_hours,
        search_queries       = [q.strip() for q in settings.search_queries.split(",") if q.strip()],
    )
