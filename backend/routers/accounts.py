from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from ..audit import audit
from ..auth import hash_pw, require_position
from ..database import get_db
from ..models import User
from ..schemas import PositionIn, RegisterIn, StatusIn

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

@router.post("/register", status_code=201)
def register(body: RegisterIn, request: Request = None, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == body.username) |
                             (User.email == body.email)).first():
        raise HTTPException(409, "Username or email already taken")
    if body.phone_number and db.query(User).filter(
            User.phone_number == body.phone_number).first():
        raise HTTPException(409, "Phone number already registered")
    uid = body.uid or f"RG-{datetime.now(timezone.utc):%Y}-{db.query(User).count() + 1:04d}"
    if db.query(User).filter(User.uid == uid).first():
        raise HTTPException(409, "UID already taken")
    user = User(uid=uid, username=body.username, email=body.email,
                hashed_password=hash_pw(body.password), position=body.position,
                phone_number=body.phone_number)          # ← Edit A lives here
    db.add(user); db.commit(); db.refresh(user)
    audit(db, user.id, "register", ip=request.client.host if request else None)
    return {"uid": user.uid, "username": user.username, "position": user.position}

@router.get("/me")
def me(user: User = Depends(require_position("administrator", "officer", "viewer"))):
    return {"uid": user.uid, "username": user.username, "email": user.email,
            "position": user.position, "mfa_enabled": user.mfa_enabled,
            "phone_number": user.phone_number,           # ← Edit B lives here
            "last_login": user.last_login}

@router.get("")
def list_accounts(admin: User = Depends(require_position("administrator")),
                  db: Session = Depends(get_db)):
    return [{"uid": u.uid, "username": u.username, "email": u.email,
             "position": u.position, "is_active": u.is_active,
             "mfa_enabled": u.mfa_enabled,
             "phone_number": u.phone_number} for u in db.query(User).all()]

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