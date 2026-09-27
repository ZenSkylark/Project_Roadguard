from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..audit import audit
from ..auth import (get_current_user, hash_pw, require_position,
                    new_opaque_token, reset_hash, utcnow)
from ..config import settings
from ..database import get_db
from ..models import User
from ..ratelimit import rate_limit
from ..schemas import PositionIn, ProfileUpdateIn, RegisterIn, StatusIn
from ..services.mailer import send_mail

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request = None,
             _rl=Depends(rate_limit), db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == body.username) |
                             (User.email == body.email)).first():
        raise HTTPException(409, "Username or email already taken")
    uid = body.uid or f"RG-{utcnow():%Y}-{db.query(User).count() + 1:04d}"
    if db.query(User).filter(User.uid == uid).first():
        raise HTTPException(409, "UID already taken")
    need_verify = settings.REQUIRE_EMAIL_VERIFICATION
    user = User(uid=uid, username=body.username, email=body.email,
                hashed_password=hash_pw(body.password), position=body.position,
                email_verified=not need_verify)
    verify_raw = None
    if need_verify:
        verify_raw = new_opaque_token()
        user.verify_token = reset_hash(verify_raw)
        user.verify_expires = utcnow() + timedelta(hours=24)
    db.add(user); db.commit(); db.refresh(user)
    audit(db, user.id, "register", ip=request.client.host if request else None)
    if need_verify:
        send_mail(user.email, "Verify your Roadguard email",
                  f"Verification token (valid 24h):\n{verify_raw}")
    return {"uid": user.uid, "username": user.username,
            "position": user.position, "verification_required": need_verify}

@router.get("/me")
def me(user: User = Depends(require_position("administrator", "officer", "viewer"))):
    return {"uid": user.uid, "username": user.username, "email": user.email,
            "position": user.position, "mfa_enabled": user.mfa_enabled,
            "email_verified": user.email_verified, "last_login": user.last_login}

@router.patch("/me")
def update_me(body: ProfileUpdateIn, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    if body.username is not None and body.username != user.username:
        if db.query(User).filter(User.username == body.username).first():
            raise HTTPException(409, "Username taken")
        user.username = body.username
    if body.email is not None and body.email != user.email:
        if db.query(User).filter(User.email == body.email).first():
            raise HTTPException(409, "Email taken")
        user.email = body.email
    db.commit()
    audit(db, user.id, "profile_updated")
    return {"username": user.username, "email": user.email}

@router.get("")
def list_accounts(admin: User = Depends(require_position("administrator")),
                  db: Session = Depends(get_db)):
    return [{"uid": u.uid, "username": u.username, "email": u.email,
             "position": u.position, "is_active": u.is_active,
             "mfa_enabled": u.mfa_enabled, "email_verified": u.email_verified}
            for u in db.query(User).all()]

@router.patch("/{uid}/position")
def set_position(uid: str, body: PositionIn,
                 admin: User = Depends(require_position("administrator")),
                 db: Session = Depends(get_db)):
    if body.position not in ("administrator", "officer", "viewer"):
        raise HTTPException(400, "Invalid position")
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.position = body.position
    db.commit()
    audit(db, admin.id, "position_changed", f"{uid} -> {body.position}")
    return {"uid": uid, "position": user.position}

@router.patch("/{uid}/status")
def set_status(uid: str, body: StatusIn,
               admin: User = Depends(require_position("administrator")),
               db: Session = Depends(get_db)):
    user = db.query(User).filter(User.uid == uid).first()
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = body.is_active
    db.commit()
    audit(db, admin.id, "status_changed", f"{uid} -> {body.is_active}")
    return {"uid": uid, "is_active": user.is_active}