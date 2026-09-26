import re
from pydantic import BaseModel, EmailStr, field_validator

PW_RULE = "Min 8 chars with upper, lower, and number"

def _check_pw(v: str) -> str:
    if len(v) < 8 or not re.search(r"[A-Z]", v) \
       or not re.search(r"[a-z]", v) or not re.search(r"\d", v):
        raise ValueError(PW_RULE)
    return v

class RegisterIn(BaseModel):
    uid: str | None = None
    username: str
    email: EmailStr
    password: str
    position: str = "viewer"

    @field_validator("username")
    @classmethod
    def _username(cls, v):
        if not re.fullmatch(r"[a-z0-9_]{3,20}", v):
            raise ValueError("3-20 chars: lowercase, digits, underscore")
        return v

    _pw = field_validator("password")(_check_pw)

    @field_validator("position")
    @classmethod
    def _position(cls, v):
        if v not in ("officer", "viewer"):      # administrator only by promotion
            raise ValueError("Self-registration allows officer or viewer")
        return v

class PasswordIn(BaseModel):
    old_password: str
    new_password: str
    _pw = field_validator("new_password")(_check_pw)

class ForgotIn(BaseModel):
    email: EmailStr

class ResetIn(BaseModel):
    token: str
    new_password: str

class MfaVerifyIn(BaseModel):
    mfa_token: str
    code: str

class MfaEnableIn(BaseModel):
    code: str

class PositionIn(BaseModel):
    position: str

class StatusIn(BaseModel):
    is_active: bool

class PlateIn(BaseModel):
    plate_text: str

    @field_validator("plate_text")
    @classmethod
    def _plate(cls, v):
        v = re.sub(r"[^A-Za-z0-9]", "", v).upper()
        if not re.fullmatch(r"[A-Z]{3}\d{3,4}", v):
            raise ValueError("Plate format: ABC1234 or ABC12345")
        return v