# app/schemas.py
from pydantic import BaseModel, EmailStr
from datetime import datetime


# ── GPU Price ─────────────────────────────────────────────────────────────────

class GPUPriceResponse(BaseModel):
    id:         str
    name:       str
    price:      float
    link:       str | None
    query:      str | None
    retailer:   str
    scraped_at: datetime | None

    class Config:
        from_attributes = True


# ── Price Alert ───────────────────────────────────────────────────────────────

class PriceAlertResponse(BaseModel):
    id:         str
    gpu_name:   str
    old_price:  float
    new_price:  float
    drop_pct:   float
    score:      float
    grade:      str
    link:       str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


# ── User Settings ─────────────────────────────────────────────────────────────

class UserSettingsUpdate(BaseModel):
    email_enabled:        bool        = False
    alert_threshold:      float       = 5.0
    check_interval_hours: float       = 6.0
    search_queries:       list[str]   = ["3090", "3080", "4090"]


class UserSettingsResponse(BaseModel):
    email_enabled:        bool
    alert_threshold:      float
    check_interval_hours: float
    search_queries:       list[str]   # returned as a list, stored as comma-separated string

    class Config:
        from_attributes = True


# ── Auth (ready for Stage 3) ──────────────────────────────────────────────────

class UserCreate(BaseModel):
    email:    EmailStr
    password: str


class UserResponse(BaseModel):
    id:         str
    email:      str
    created_at: datetime | None

    class Config:
        from_attributes = True

# ── Auth ─────────────────────────────────────────────────────────────────────

class UserResponse(BaseModel):
    id:         str
    email:      str
    created_at: datetime | None

    model_config = {"from_attributes": True}

# ── Auth ─────────────────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str