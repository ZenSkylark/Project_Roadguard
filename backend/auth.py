import secrets
from datetime import datetime, timedelta
import hashlib
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

security = HTTPBearer()


def hash_pw(password: str) -> str:
    """Hash a password using bcrypt."""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain password against its bcrypt hash."""
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def new_otp() -> str:
    """Generate a 6-digit one-time password."""
    return f"{secrets.randbelow(1000000):06d}"


def otp_hash(code: str) -> str:
    """Hash an OTP for secure storage."""
    return hashlib.sha256(code.encode()).hexdigest()


def create_token(payload: dict, expires_minutes: int = None) -> str:
    """Create a JWT token."""
    to_encode = payload.copy()
    expires = datetime.utcnow() + timedelta(
        minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expires})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get the current authenticated user."""
    payload = decode_token(credentials.credentials)
    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


def require_position(*positions: str):
    """FastAPI dependency factory for role-based access control."""
    def checker(user: User = Depends(get_current_user)):
        if user.position not in positions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {', '.join(positions)}"
            )
        return user
    return checker


def check_lockout(user: User) -> None:
    """Check if user account is currently locked."""
    if user and user.locked_until and user.locked_until > datetime.utcnow():
        remaining = (user.locked_until - datetime.utcnow()).seconds
        raise HTTPException(
            status_code=423,
            detail=f"Account locked. Try again in {remaining} seconds."
        )


def lock_if_needed(user: User, max_attempts: int = 5, lock_minutes: int = 15) -> None:
    """Lock account after too many failed login attempts."""
    if user.failed_attempts >= max_attempts:
        user.locked_until = datetime.utcnow() + timedelta(minutes=lock_minutes)


def seed_admin() -> None:
    """Create default admin user if none exists."""
    from .database import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                uid="RG-0000-0001",
                username="admin",
                email="admin@roadguard.ph",
                hashed_password=hash_pw("Admin123!"),
                position="administrator",
                is_active=True,
                mfa_enabled=False,
            )
            db.add(admin)
            db.commit()
    finally:
        db.close()