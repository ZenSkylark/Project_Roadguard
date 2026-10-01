import re
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..auth import hash_pw, get_current_user, require_position
from ..database import get_db
from ..models import User
from ..audit import audit

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


# ---------- Request Models ----------
class RegisterIn(BaseModel):
    username: str
    email: EmailStr
    password: str
    position: str = "viewer"


class UpdateMeIn(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None


class PositionIn(BaseModel):
    position: str


class StatusIn(BaseModel):
    is_active: bool


# ---------- Helpers ----------
def _generate_uid(db: Session) -> str:
    """Generate a unique UID in the format RG-YYYY-NNNN."""
    year = datetime.utcnow().year
    count = db.query(User).count()
    while True:
        count += 1
        uid = f"RG-{year}-{count:04d}"
        exists = db.query(User).filter(User.uid == uid).first()
        if not exists:
            return uid


def _validate_password(password: str):
    """Enforce password strength: 8+ chars, upper, lower, digit."""
    if len(password) < 8:
        raise HTTPException(422, "Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(422, "Password must contain an uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(422, "Password must contain a lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(422, "Password must contain a number")


def _user_response(user: User) -> dict:
    """Standard user payload including verification status."""
    return {
        "uid": user.uid,
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "phone_number": user.phone_number,
        "phone_verified": user.phone_verified,
        "position": user.position,
        "mfa_enabled": user.mfa_enabled,
        "mfa_method": user.mfa_method,
        "last_login": user.last_login.isoformat() if user.last_login else None,
    }


# ---------- Registration ----------
@router.post("/register", status_code=201)
def register(body: RegisterIn, db: Session = Depends(get_db)):
    # Block self-registration as administrator
    if body.position == "administrator":
        raise HTTPException(422, "Cannot self-register as administrator")

    # Validate position is a known non-admin role
    if body.position not in ("viewer", "officer"):
        raise HTTPException(422, "Invalid position")

    # Validate password strength
    _validate_password(body.password)

    # Check for reserved or duplicate username
    if body.username.lower() == "admin":
        raise HTTPException(409, "Username is reserved")
    existing = db.query(User).filter(User.username == body.username).first()
    if existing:
        raise HTTPException(409, "Username already taken")

    # Check for duplicate email
    existing_email = db.query(User).filter(User.email == body.email).first()
    if existing_email:
        raise HTTPException(409, "Email already registered")

    new_user = User(
        uid=_generate_uid(db),
        username=body.username,
        email=body.email,
        hashed_password=hash_pw(body.password),
        position=body.position,
        is_active=True,
        mfa_enabled=False,
        email_verified=False,   # ✅ Not verified by default
        phone_verified=False,   # ✅ Not verified by default
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "uid": new_user.uid,
        "username": new_user.username,
        "email": new_user.email,
        "position": new_user.position,
        "email_verified": new_user.email_verified,
        "phone_verified": new_user.phone_verified,
    }


# ---------- Current User ----------
@router.get("/me")
def get_me(user: User = Depends(get_current_user)):
    return _user_response(user)


@router.patch("/me")
def update_me(body: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    changed = False
    
    if "email" in body and body["email"] != user.email:
        user.email = body["email"]
        user.email_verified = False  # Reset verification when email changes
        changed = True
    
    if "phone_number" in body and body["phone_number"] != user.phone_number:
        user.phone_number = body["phone_number"]
        user.phone_verified = False  # Reset verification when phone changes
        changed = True
    
    if changed:
        db.commit()
        audit(db, user.id, "profile_updated")
    
    return {
        "uid": user.uid,
        "username": user.username,
        "email": user.email,
        "email_verified": user.email_verified,
        "phone_number": user.phone_number,
        "phone_verified": user.phone_verified,
        "position": user.position,
        "mfa_enabled": user.mfa_enabled,
        "mfa_method": user.mfa_method,
    }


# ---------- Admin: Account Management ----------
@router.get("")
def list_accounts(user: User = Depends(require_position("administrator")),
                  db: Session = Depends(get_db)):
    users = db.query(User).all()
    return [
        {
            "uid": u.uid,
            "username": u.username,
            "email": u.email,
            "position": u.position,
            "is_active": u.is_active,
            "email_verified": u.email_verified,
            "phone_verified": u.phone_verified,
            "mfa_enabled": u.mfa_enabled,
        }
        for u in users
    ]


@router.patch("/{uid}/position")
def update_position(uid: str, body: PositionIn,
                    user: User = Depends(require_position("administrator")),
                    db: Session = Depends(get_db)):
    target = db.query(User).filter(User.uid == uid).first()
    if not target:
        raise HTTPException(404, "User not found")
    if body.position not in ("viewer", "officer", "administrator"):
        raise HTTPException(422, "Invalid position")
    target.position = body.position
    db.commit()
    db.refresh(target)
    return {"uid": target.uid, "username": target.username, "position": target.position}


@router.patch("/{uid}/status")
def update_status(uid: str, body: StatusIn,
                  user: User = Depends(require_position("administrator")),
                  db: Session = Depends(get_db)):
    target = db.query(User).filter(User.uid == uid).first()
    if not target:
        raise HTTPException(404, "User not found")
    target.is_active = body.is_active
    db.commit()
    db.refresh(target)
    return {"uid": target.uid, "username": target.username, "is_active": target.is_active}