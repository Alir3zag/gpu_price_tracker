# ============================================================
# routers/auth.py — three endpoints: register, login, me
# ============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_async_session, User
from app.schemas import UserCreate, UserResponse, TokenResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])
# APIRouter is a mini-app you attach to the main FastAPI app in main.py.
# prefix="/auth" means every route here automatically starts with /auth —
# so @router.post("/register") becomes POST /auth/register.
# tags=["auth"] just groups them together in the /docs UI.


# ── Register ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserCreate,
    session: AsyncSession = Depends(get_async_session)
):
    """Create a new account.

    1. Check no account already exists with that email
    2. Hash the password
    3. Save the new User row to the DB
    4. Return the user (without password)
    """
    # check email isn't already taken
    result = await session.execute(select(User).where(User.email == body.email))
    existing = result.scalars().first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with that email already exists"
        )

    user = User(
        email    = body.email,
        password = hash_password(body.password),
        # hash_password turns "mypassword123" into "$2b$12$..." — never stored plain
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    # refresh pulls the DB-generated fields (id, created_at) back into the object

    return user


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_async_session)
):
    """Verify credentials and return a JWT token.

    OAuth2PasswordRequestForm expects the request body as form data
    (not JSON) with fields "username" and "password".
    We treat "username" as the email field.
    This is the OAuth2 spec — the /docs UI login button depends on it.

    1. Look up the user by email
    2. Verify the password against the stored hash
    3. Create and return a signed JWT
    """
    result = await session.execute(select(User).where(User.email == form.username))
    user = result.scalars().first()

    # deliberately vague error — don't tell attackers whether
    # the email exists or just the password was wrong
    if not user or not verify_password(form.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(user_id=user.id)
    return {"access_token": token, "token_type": "bearer"}
    # token_type: "bearer" is part of the OAuth2 spec —
    # tells the client to send the token as "Authorization: Bearer <token>"


# ── Me ────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    """Return the currently logged-in user's info.

    get_current_user (from auth.py) runs first —
    it pulls the token from the header, verifies it,
    and injects the User object directly.
    If the token is missing or invalid, it never reaches here.
    """
    return current_user
