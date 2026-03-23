# ============================================================
# auth.py — password hashing, JWT creation, JWT verification,
#           and the current_user dependency every protected
#           endpoint will use
# ============================================================

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_MIN
from app.db import get_async_session, User


# ── Password hashing ──────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
# CryptContext is a passlib object that knows which hashing algorithm to use.
# schemes=["bcrypt"] means all passwords are hashed with bcrypt — a slow,
# intentionally expensive algorithm that makes brute-force attacks impractical.
# deprecated="auto" means if you ever switch algorithms in the future,
# old hashes are automatically flagged for rehashing.

def hash_password(plain: str) -> str:
    """Turn a plain-text password into a bcrypt hash. Called once at registration."""
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    """Check a login attempt. bcrypt re-hashes the plain password and compares.
    Returns True if they match, False otherwise. The original password is never stored."""
    return pwd_context.verify(plain, hashed)


# ── JWT creation ──────────────────────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    """Build and sign a JWT token that encodes who the user is and when it expires.

    A JWT has three parts: header.payload.signature
    - header: algorithm used (HS256)
    - payload: the data we store inside (sub = user id, exp = expiry time)
    - signature: header + payload signed with JWT_SECRET
                 → if anyone tampers with the payload, the signature breaks
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MIN)
    # sub (subject) is the standard JWT claim for "who this token belongs to"
    payload = {"sub": user_id, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


# ── JWT verification ──────────────────────────────────────────────────────────

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
# OAuth2PasswordBearer tells FastAPI:
# "tokens for this app come from /auth/login"
# "on every protected endpoint, pull the token from the
#  Authorization: Bearer <token> header automatically"
# It doesn't verify anything itself — that's what get_current_user does below.

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_async_session),
) -> User:
    """Dependency injected into every protected endpoint.
    FastAPI calls this automatically before the endpoint runs.

    Flow:
    1. OAuth2PasswordBearer pulls the token from the Authorization header
    2. We decode and verify the JWT signature
    3. We extract the user_id from the payload
    4. We fetch and return the real User row from the DB

    If anything fails (missing token, bad signature, expired, user deleted)
    → 401 is raised and the endpoint never runs.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
        # WWW-Authenticate header is part of the HTTP spec —
        # tells the client what kind of auth is expected
    )

    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        # jwt.decode verifies the signature AND checks exp automatically.
        # If the token was tampered with or expired → raises JWTError.
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()

    if user is None:
        # Token was valid but the user was deleted from the DB after it was issued
        raise credentials_exception

    return user
    # FastAPI injects this User object directly into the endpoint function —
    # e.g. async def get_prices(current_user: User = Depends(get_current_user))