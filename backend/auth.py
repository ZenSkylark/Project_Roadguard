import hashlib
import secrets
from datetime import datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from .audit import audit
from .config import settings
from .database import get_db
from .models import User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
LOCK_THRESHOLD, LOCK_MINUTES = 5, 15

# ---------------- password hashing (bcrypt direct) ----------------
hash_pw = lambda pw: bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
verify_pw = lambda pw, h: bcrypt.checkpw(pw.encode("utf-8"), h.encode("utf-8"))

# ---------------- password-reset tokens ----------------
reset_hash = lambda token: hashlib.sha256(token.encode()).hexdigest()
new_reset_token = lambda: secrets.token_urlsafe(32)

# ---------------- SMS one-time codes ----------------
new_otp = lambda: f"{secrets.randbelow(1_000_000):06d}"
otp_hash = lambda code: hashlib.sha256(code.encode()).hexdigest()

# ---------------- JWT ----------------
def create_token(user: User, scope: str = "access", minutes: int | None = None) -> str:
    minutes = minutes or (5 if scope == "mfa" else settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    exp = datetime.utcnow() + timedelta(minutes=minutes)
    return jwt.encode({"sub": user.username, "scope": scope, "role": user.position,
                       "exp": exp}, settings.SECRET_KEY, settings.ALGORITHM)

def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        p = jwt.decode(token, settings.SECRET_KEY, [settings.ALGORITHM])
        if p.get("scope") != "access":
            raise JWTError()
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.query(User).filter(User.username == p.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(401, "User not found or disabled")
    return user

def require_position(*allowed: str):
    def dep(user: User = Depends(get_current_user)):
        if user.position not in allowed:
            raise HTTPException(403, f"Requires position: {', '.join(allowed)}")
        return user
    return dep

# ---------------- brute-force lockout ----------------
def lock_if_needed(db: Session, user: User, ip: str | None):
    user.failed_logins += 1
    if user.failed_logins >= LOCK_THRESHOLD:
        user.locked_until = datetime.utcnow() + timedelta(minutes=LOCK_MINUTES)
        audit(db, user.id, "account_locked", f"{LOCK_MINUTES} min", ip)
    db.commit()

# ---------------- first-run admin seed ----------------
def seed_admin():
    from .database import SessionLocal
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(uid="RG-2026-0000", username="admin",
                    email="admin@roadguard.ph",
                    hashed_password=hash_pw("Admin123!"),
                    position="administrator"))
        db.commit()
    db.close()