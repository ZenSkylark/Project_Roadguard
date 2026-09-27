import hashlib, secrets
from datetime import datetime, timedelta
import bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from .audit import audit
from .config import settings
from .database import get_db
from .models import RefreshToken, User

oauth2 = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
LOCK_THRESHOLD, LOCK_MINUTES = 5, 15

hash_pw = lambda pw: bcrypt.hashpw(pw.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
verify_pw = lambda pw, h: bcrypt.checkpw(pw.encode("utf-8"), h.encode("utf-8"))
reset_hash = lambda token: hashlib.sha256(token.encode()).hexdigest()
new_opaque_token = lambda: secrets.token_urlsafe(32)

def utcnow():
    return datetime.utcnow()          # naive UTC: matches SQLite storage

def create_token(user: User, scope: str = "access", minutes: int | None = None) -> str:
    minutes = minutes or (5 if scope == "mfa" else settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user.username, "scope": scope, "role": user.position,
               "exp": utcnow() + timedelta(minutes=minutes)}
    if scope == "access":
        payload["ver"] = user.token_version      # A2: session generation
    return jwt.encode(payload, settings.SECRET_KEY, settings.ALGORITHM)

def issue_refresh(db: Session, user: User) -> str:
    raw = secrets.token_urlsafe(48)
    db.add(RefreshToken(user_id=user.id, token_hash=reset_hash(raw),
                        expires_at=utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)))
    db.commit()
    return raw

def rotate_refresh(db: Session, raw: str):
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == reset_hash(raw)).first()
    if not rt or rt.revoked or rt.expires_at < utcnow():
        return None, None
    rt.revoked = True                            # A2: rotation — old refresh dies
    user = db.get(User, rt.user_id)
    db.commit()
    if not user or not user.is_active:
        return None, None
    return user, issue_refresh(db, user)

def revoke_all_refresh(db: Session, user: User):
    db.query(RefreshToken).filter(RefreshToken.user_id == user.id,
                                  RefreshToken.revoked == False).update({"revoked": True})
    db.commit()

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
    if p.get("ver", 0) != user.token_version:
        raise HTTPException(401, "Session revoked. Log in again.")
    return user

def require_position(*allowed: str):
    def dep(user: User = Depends(get_current_user)):
        if user.position not in allowed:
            raise HTTPException(403, f"Requires position: {', '.join(allowed)}")
        return user
    return dep

def lock_if_needed(db: Session, user: User, ip: str | None):
    user.failed_logins += 1
    if user.failed_logins >= LOCK_THRESHOLD:
        user.locked_until = utcnow() + timedelta(minutes=LOCK_MINUTES)
        audit(db, user.id, "account_locked", f"{LOCK_MINUTES} min", ip)
    db.commit()

def seed_admin():
    from .database import SessionLocal
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(uid="RG-2026-0000", username="admin",
                    email="admin@roadguard.ph",
                    hashed_password=hash_pw("Admin123!"),
                    position="administrator", email_verified=True))
        db.commit()
    db.close()