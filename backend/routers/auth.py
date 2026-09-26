import io
from datetime import datetime, timedelta
import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from ..audit import audit
from ..auth import (create_token, get_current_user, hash_pw, verify_pw,
                    lock_if_needed, new_reset_token, reset_hash)
from ..config import settings
from ..database import get_db
from ..models import User
from ..schemas import ForgotIn, MfaEnableIn, MfaVerifyIn, PasswordIn, ResetIn
from ..services.mailer import send_mail

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), request: Request = None,
          db: Session = Depends(get_db)):
    ip = request.client.host if request else None
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_pw(form.password, user.hashed_password):
        if user:
            lock_if_needed(db, user, ip)
        raise HTTPException(401, "Bad credentials")
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(423, "Account locked. Try again later.")
    if not user.is_active:
        raise HTTPException(403, "Account disabled")
    user.failed_logins = 0
    user.last_login = datetime.utcnow()
    db.commit()
    audit(db, user.id, "login", ip=ip)
    if user.mfa_enabled:
        return {"mfa_required": True, "mfa_token": create_token(user, "mfa")}
    return {"access_token": create_token(user), "token_type": "bearer",
            "position": user.position, "uid": user.uid}

@router.post("/mfa/verify")
def mfa_verify(body: MfaVerifyIn, db: Session = Depends(get_db)):
    try:
        p = jwt.decode(body.mfa_token, settings.SECRET_KEY, [settings.ALGORITHM])
        if p.get("scope") != "mfa":
            raise JWTError()
    except JWTError:
        raise HTTPException(401, "MFA session invalid")
    user = db.query(User).filter(User.username == p.get("sub")).first()
    if not user or not user.mfa_secret \
       or not pyotp.TOTP(user.mfa_secret).verify(body.code, valid_window=1):
        raise HTTPException(401, "Invalid code")
    audit(db, user.id, "mfa_login")
    return {"access_token": create_token(user), "token_type": "bearer"}

@router.post("/mfa/setup")
def mfa_setup(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user.mfa_secret = pyotp.random_base32()
    db.commit()
    return {"secret": user.mfa_secret,
            "uri": pyotp.TOTP(user.mfa_secret).provisioning_uri(user.username, "Roadguard")}

@router.get("/mfa/qr")
def mfa_qr(user: User = Depends(get_current_user)):
    if not user.mfa_secret:
        raise HTTPException(400, "Run /mfa/setup first")
    uri = pyotp.TOTP(user.mfa_secret).provisioning_uri(user.username, "Roadguard")
    buf = io.BytesIO()
    qrcode.make(uri).save(buf, format="PNG")
    return Response(buf.getvalue(), media_type="image/png")

@router.post("/mfa/enable")
def mfa_enable(body: MfaEnableIn, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    if not user.mfa_secret \
       or not pyotp.TOTP(user.mfa_secret).verify(body.code, valid_window=1):
        raise HTTPException(400, "Wrong code - MFA not enabled")
    user.mfa_enabled = True
    db.commit()
    audit(db, user.id, "mfa_enabled")
    return {"mfa_enabled": True}

@router.post("/change-password")
def change_password(body: PasswordIn, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_pw(body.old_password, user.hashed_password):
        raise HTTPException(400, "Current password wrong")
    user.hashed_password = hash_pw(body.new_password)
    db.commit()
    audit(db, user.id, "password_changed")
    return {"message": "Password updated"}

@router.post("/forgot-password")
def forgot(body: ForgotIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if user:
        token = new_reset_token()
        user.reset_token = reset_hash(token)
        user.reset_expires = datetime.utcnow() + timedelta(minutes=30)
        db.commit()
        send_mail(user.email, "Roadguard password reset",
                  f"Use this token within 30 minutes:\n{token}")
    return {"message": "If that email exists, a reset token was sent."}

@router.post("/reset-password")
def reset(body: ResetIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == reset_hash(body.token)).first()
    if not user or not user.reset_expires or user.reset_expires < datetime.utcnow():
        raise HTTPException(400, "Invalid or expired token")
    user.hashed_password = hash_pw(body.new_password)
    user.reset_token = user.reset_expires = None
    user.failed_logins = 0
    user.locked_until = None
    db.commit()
    audit(db, user.id, "password_reset")
    return {"message": "Password reset. You can log in now."}