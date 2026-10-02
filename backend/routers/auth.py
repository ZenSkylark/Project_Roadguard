from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Form
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ..audit import audit
from ..auth import (
    verify_password, hash_pw, create_token, decode_token,
    get_current_user, new_otp, otp_hash, check_lockout, lock_if_needed
)
from ..clock import utcnow
from ..database import get_db
from ..models import User
from ..services.email import send_email
from ..services.sms import send_sms

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_OTP_ATTEMPTS = 5


# ─── OTP helpers ─────────────────────────────────────────────────────────────

def _otp_fail(user: User, db: Session, msg: str = "Invalid OTP"):
    """Track wrong attempts; invalidate the code after too many tries."""
    user.otp_attempts = (user.otp_attempts or 0) + 1
    if user.otp_attempts >= MAX_OTP_ATTEMPTS:
        user.otp_hash = None
        user.otp_expires = None
        user.otp_attempts = 0
        db.commit()
        raise HTTPException(401, "Too many wrong attempts. Request a new code.")
    db.commit()
    remaining = MAX_OTP_ATTEMPTS - user.otp_attempts
    raise HTTPException(401, f"{msg}. {remaining} attempt(s) remaining.")


def _clear_otp(user: User):
    user.otp_hash = None
    user.otp_expires = None
    user.otp_attempts = 0


def _issue_otp(user: User, db: Session, minutes: int = 5) -> str:
    code = new_otp()
    user.otp_hash = otp_hash(code)
    user.otp_expires = utcnow() + timedelta(minutes=minutes)
    user.otp_attempts = 0
    db.commit()
    return code


def _send_mfa_otp(user: User, db: Session, purpose: str = "login", method: str = None):
    code = _issue_otp(user, db, minutes=5)
    send_method = method or user.mfa_method
    if send_method == "email":
        send_email(user.email, "Roadguard Login Code",
                   f"Your Roadguard {purpose} code: {code}\n\nValid for 5 minutes.")
    else:
        send_sms(user.phone_number,
                 f"Roadguard {purpose} code: {code} (valid 5 minutes)")


# ─── Pydantic models ─────────────────────────────────────────────────────────

class ChangePasswordIn(BaseModel):
    old_password: str
    new_password: str
    code: str | None = None


class MfaSetupIn(BaseModel):
    method: str
    phone_number: str | None = None


class MfaVerifyIn(BaseModel):
    code: str


class MfaLoginVerifyIn(BaseModel):
    mfa_token: str
    code: str


class MfaRequestCodeIn(BaseModel):
    mfa_token: str
    method: str


class MfaResendIn(BaseModel):
    mfa_token: str
    method: str


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str


class EmailVerifyIn(BaseModel):
    email: EmailStr


class EmailConfirmVerifyIn(BaseModel):
    email: EmailStr
    code: str


class PhoneVerifyIn(BaseModel):
    phone_number: str


class PhoneConfirmVerifyIn(BaseModel):
    phone_number: str
    code: str


# ─── Login ───────────────────────────────────────────────────────────────────

@router.post("/login")
def login(request: Request, db: Session = Depends(get_db),
          username: str = Form(...), password: str = Form(...)):
    user = db.query(User).filter(User.username == username).first()
    check_lockout(user)

    if not user or not verify_password(password, user.hashed_password):
        if user:
            user.failed_attempts += 1
            lock_if_needed(user)
            db.commit()
        audit(db, user.id if user else None, "login_failed", f"ip={request.client.host}")
        raise HTTPException(401, "Invalid credentials")

    if not user.is_active:
        raise HTTPException(403, "Account disabled")

    user.failed_attempts = 0
    user.locked_until = None

    if user.mfa_enabled:
        token = create_token({"sub": str(user.id), "mfa_pending": True}, expires_minutes=5)
        available_methods = []
        if user.email:
            available_methods.append("email")
        if user.phone_number:
            available_methods.append("sms")
        audit(db, user.id, "login_mfa_required", f"methods={','.join(available_methods)}")
        return {
            "mfa_required": True,
            "mfa_token": token,
            "available_methods": available_methods,
            "method": user.mfa_method
        }

    user.last_login = utcnow()
    db.commit()
    token = create_token({"sub": str(user.id)})
    audit(db, user.id, "login_success", f"ip={request.client.host}")
    return {"access_token": token, "token_type": "bearer"}


# ─── MFA login flow ──────────────────────────────────────────────────────────

@router.post("/mfa/request-code")
def request_mfa_code(body: MfaRequestCodeIn, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.mfa_token)
    except Exception:
        raise HTTPException(401, "Invalid MFA token")

    if not payload.get("mfa_pending"):
        raise HTTPException(400, "Token not pending MFA")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, "User not found")

    if body.method == "email" and not user.email:
        raise HTTPException(400, "Email MFA is not available for this account")
    if body.method == "sms" and not user.phone_number:
        raise HTTPException(400, "SMS MFA is not available for this account")
    if body.method not in ("email", "sms"):
        raise HTTPException(400, "Invalid MFA method")

    _send_mfa_otp(user, db, purpose="login", method=body.method)
    return {"message": f"Code sent via {body.method}"}


@router.post("/mfa/verify-login")
def verify_mfa_login(body: MfaLoginVerifyIn, request: Request, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.mfa_token)
    except Exception:
        raise HTTPException(401, "Invalid MFA token")

    if not payload.get("mfa_pending"):
        raise HTTPException(400, "Token not pending MFA")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(401, "User not found")

    if not user.otp_hash or not user.otp_expires:
        raise HTTPException(400, "No OTP issued")
    if user.otp_expires < utcnow():
        raise HTTPException(401, "OTP expired")
    if user.otp_hash != otp_hash(body.code.strip()):
        _otp_fail(user, db, "Invalid OTP")

    _clear_otp(user)
    user.last_login = utcnow()
    db.commit()

    token = create_token({"sub": str(user.id)})
    audit(db, user.id, "login_mfa_verified", f"ip={request.client.host}")
    return {"access_token": token, "token_type": "bearer"}


@router.post("/mfa/resend")
def resend_mfa(body: MfaResendIn, db: Session = Depends(get_db)):
    try:
        payload = decode_token(body.mfa_token)
    except Exception:
        raise HTTPException(401, "Invalid MFA token")

    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user or not user.mfa_enabled:
        raise HTTPException(400, "MFA not enabled")

    _send_mfa_otp(user, db, purpose="login", method=body.method)
    return {"message": "Code resent"}


# ─── MFA setup & management ──────────────────────────────────────────────────

@router.post("/mfa/setup")
def setup_mfa(body: MfaSetupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if body.method == "sms":
        if not body.phone_number:
            raise HTTPException(400, "Phone number required for SMS MFA")
        user.phone_number = body.phone_number
        user.mfa_method = "sms"
    elif body.method == "email":
        if not user.email_verified:
            raise HTTPException(400, "Email must be verified before enabling Email MFA")
        user.mfa_method = "email"
    else:
        raise HTTPException(400, "Invalid MFA method")

    code = _issue_otp(user, db, minutes=5)

    if body.method == "email":
        send_email(user.email, "Roadguard MFA Setup",
                   f"Your MFA setup code: {code}\n\nValid for 5 minutes.")
    else:
        send_sms(user.phone_number, f"Roadguard MFA setup code: {code} (valid 5 minutes)")

    audit(db, user.id, "mfa_setup_initiated", f"method={body.method}")
    return {"message": "OTP sent"}


@router.post("/mfa/enable")
def enable_mfa(body: MfaVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.otp_hash or not user.otp_expires:
        raise HTTPException(400, "No OTP issued")
    if user.otp_expires < utcnow():
        raise HTTPException(401, "OTP expired")
    if user.otp_hash != otp_hash(body.code):
        _otp_fail(user, db, "Invalid OTP")

    user.mfa_enabled = True
    _clear_otp(user)

    if user.mfa_method == "email":
        user.email_verified = True

    db.commit()

    detail = f"method={user.mfa_method}"
    if user.mfa_method == "email":
        detail += " (email verified)"
    audit(db, user.id, "mfa_enabled", detail)
    return {"message": "MFA enabled", "email_verified": user.email_verified}


@router.post("/mfa/disable")
def disable_mfa(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = _issue_otp(user, db, minutes=5)

    if user.mfa_method == "email":
        send_email(user.email, "Roadguard MFA Disable",
                   f"Your MFA disable code: {code}\n\nValid for 5 minutes.")
    else:
        send_sms(user.phone_number, f"Roadguard MFA disable code: {code} (valid 5 minutes)")

    return {"message": "Confirmation code sent"}


@router.post("/mfa/confirm-disable")
def confirm_disable_mfa(body: MfaVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.otp_hash or not user.otp_expires:
        raise HTTPException(400, "No OTP issued")
    if user.otp_expires < utcnow():
        raise HTTPException(401, "Code expired")
    if user.otp_hash != otp_hash(body.code):
        _otp_fail(user, db, "Invalid code")

    user.mfa_enabled = False
    user.mfa_method = None
    _clear_otp(user)
    db.commit()

    audit(db, user.id, "mfa_disabled")
    return {"message": "MFA disabled"}


@router.post("/mfa/switch")
def switch_mfa(body: MfaSetupIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.mfa_enabled:
        raise HTTPException(400, "MFA not enabled")

    if body.method == "sms":
        if not body.phone_number:
            raise HTTPException(400, "Phone number required for SMS MFA")
        user.phone_number = body.phone_number
    elif body.method != "email":
        raise HTTPException(400, "Invalid MFA method")

    user.mfa_method = body.method
    code = _issue_otp(user, db, minutes=5)

    if body.method == "email":
        send_email(user.email, "Roadguard MFA Method Change",
                   f"Your new MFA method verification code: {code}\n\nValid for 5 minutes.")
    else:
        send_sms(body.phone_number, f"Roadguard MFA method change code: {code} (valid 5 minutes)")

    audit(db, user.id, "mfa_method_switch_initiated", f"method={body.method}")
    return {"message": "Verification code sent"}


# ─── Password management ─────────────────────────────────────────────────────

@router.post("/change-password")
def change_password(body: ChangePasswordIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(body.old_password, user.hashed_password):
        raise HTTPException(401, "Invalid current password")

    if user.mfa_enabled:
        if not body.code:
            _send_mfa_otp(user, db, "password change")
            audit(db, user.id, "password_change_challenge_sent")
            raise HTTPException(428, "MFA code required")

        if not user.otp_hash or not user.otp_expires:
            raise HTTPException(400, "No OTP issued")
        if user.otp_expires < utcnow():
            raise HTTPException(401, "OTP expired")
        if user.otp_hash != otp_hash(body.code):
            _otp_fail(user, db, "Invalid OTP")

        _clear_otp(user)

    user.hashed_password = hash_pw(body.new_password)
    db.commit()
    audit(db, user.id, "password_changed")
    return {"message": "Password changed"}


@router.post("/forgot-password")
def forgot_password(body: ForgotPasswordIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if user:
        code = new_otp()
        user.reset_hash = otp_hash(code)
        user.reset_expires = utcnow() + timedelta(minutes=15)
        db.commit()
        send_email(user.email, "Roadguard Password Reset",
                   f"Your password reset code: {code}\n\nValid for 15 minutes.")

    return {"message": "If the email exists, a reset code has been sent"}


@router.post("/reset-password")
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()

    if not user or not user.reset_hash:
        raise HTTPException(400, "Invalid reset request")
    if user.reset_expires < utcnow():
        raise HTTPException(401, "Reset code expired")
    if user.reset_hash != otp_hash(body.code):
        raise HTTPException(401, "Invalid reset code")

    user.hashed_password = hash_pw(body.new_password)
    user.reset_hash = None
    user.reset_expires = None
    db.commit()

    audit(db, user.id, "password_reset")
    return {"message": "Password reset successful"}


# ─── Email verification ──────────────────────────────────────────────────────

@router.post("/email/send-verify")
def send_email_verification(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = _issue_otp(user, db, minutes=15)
    send_email(user.email, "Roadguard Email Verification",
               f"Your email verification code: {code}\n\nValid for 15 minutes.")
    audit(db, user.id, "email_verification_sent")
    return {"message": "Verification code sent to your email"}


@router.post("/email/confirm-verify")
def confirm_email_verification(body: MfaVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.otp_hash or not user.otp_expires:
        raise HTTPException(400, "No verification code issued")
    if user.otp_expires < utcnow():
        raise HTTPException(401, "Verification code expired")
    if user.otp_hash != otp_hash(body.code):
        _otp_fail(user, db, "Invalid verification code")

    user.email_verified = True
    _clear_otp(user)
    db.commit()

    audit(db, user.id, "email_verified")
    return {"message": "Email verified successfully", "email_verified": True}


# ─── Phone verification ──────────────────────────────────────────────────────

@router.post("/phone/send-verify")
def send_phone_verification(body: PhoneVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not body.phone_number:
        raise HTTPException(400, "Phone number is required")

    user.phone_number = body.phone_number
    code = _issue_otp(user, db, minutes=15)
    send_sms(body.phone_number,
             f"Your Roadguard phone verification code: {code} (valid 15 minutes)")
    audit(db, user.id, "phone_verification_sent")
    return {"message": "Verification code sent to your phone"}


@router.post("/phone/confirm-verify")
def confirm_phone_verification(body: PhoneConfirmVerifyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.phone_number != body.phone_number:
        raise HTTPException(400, "Phone number does not match")
    if not user.otp_hash or not user.otp_expires:
        raise HTTPException(400, "No verification code issued")
    if user.otp_expires < utcnow():
        raise HTTPException(401, "Verification code expired")
    if user.otp_hash != otp_hash(body.code):
        _otp_fail(user, db, "Invalid verification code")

    user.phone_verified = True
    _clear_otp(user)
    db.commit()

    audit(db, user.id, "phone_verified")
    return {"message": "Phone verified successfully", "phone_verified": True}