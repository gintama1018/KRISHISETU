"""
KrishiSetu — API Routes: Supabase Auth & Real-Time User Management
Real Email OTP / Password Authentication + Supabase PostgreSQL Sync
"""
import os
import bcrypt
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from db.supabase_client import get_service_supabase, get_supabase

router = APIRouter()


class SignUpRequest(BaseModel):
    name: str
    email: EmailStr
    phone: str
    crop: str = "rice"
    state: str = "Assam"
    district: str = ""
    village_code: str = "ASM-KAM-001"
    plot_area_acres: float = 2.0
    language_preference: str = "English"
    password: Optional[str] = None
    consent_given: bool = True


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    token: str          # 6-digit OTP code sent to user email


class LoginRequest(BaseModel):
    email: EmailStr
    password: Optional[str] = None


@router.post("/signup")
async def signup_farmer(req: SignUpRequest):
    """
    Real-time Farmer Sign Up:
    1. Triggers real Email OTP to user's email via Supabase Auth.
    2. Writes farmer profile to Supabase 'farmers' table.
    3. Captures DPDP consent in Supabase 'consent_records' & 'audit_log'.
    """
    db_service = get_service_supabase()
    db_anon = get_supabase()
    ts = datetime.now(timezone.utc).isoformat()
    phone_hash = bcrypt.hashpw(req.phone.encode(), bcrypt.gensalt()).decode()

    # Step 1: Trigger real Email OTP or Create User in Supabase Auth
    user_id = None
    try:
        if req.password:
            # Create user with password
            auth_res = db_service.auth.admin.create_user({
                "email": req.email,
                "password": req.password,
                "email_confirm": True,
                "user_metadata": {"name": req.name, "phone": req.phone, "crop": req.crop}
            })
            if auth_res.user:
                user_id = auth_res.user.id
        else:
            # Trigger real Email OTP magic code to farmer's email
            db_anon.auth.sign_in_with_otp({"email": req.email})
    except Exception as ex:
        print(f"[AUTH SIGNUP NOTICE] Supabase Auth notice: {ex}")

    # Step 2: Insert / Upsert profile in Supabase 'farmers' table
    farmer_data = {
        "email": req.email,
        "name": req.name,
        "phone_hash": phone_hash,
        "crop": req.crop,
        "state": req.state,
        "district": req.district,
        "village_code": req.village_code,
        "area_acres": req.plot_area_acres,
        "language": req.language_preference,
        "consent_given": req.consent_given,
        "consent_timestamp": ts,
        "created_at": ts,
    }
    if user_id:
        farmer_data["id"] = user_id

    result = db_service.table("farmers").insert(farmer_data).execute()
    if not result.data:
        # Fallback if phone_hash duplicate or already exists
        result = db_service.table("farmers").select("*").eq("name", req.name).execute()

    farmer = result.data[0] if result.data else farmer_data

    # Step 3: Record DPDP Consent in Supabase
    farmer_id_str = str(farmer.get("id") or "F_" + req.phone[-4:])
    try:
        db_service.table("consent_records").upsert({
            "farmer_id": farmer_id_str,
            "phone_hash": phone_hash,
            "consent_given": True,
            "consent_method": "app",
            "consent_timestamp": ts,
            "data_uses": "weather_advisory,mandi_prices,risk_alerts",
        }, on_conflict="farmer_id").execute()

        db_service.table("audit_log").insert({
            "farmer_id": farmer_id_str,
            "action": "user_signup_realtime",
            "phone_hash": phone_hash,
            "consent_given": True,
            "created_at": ts,
        }).execute()
    except Exception as e:
        print(f"[DPDP NOTICE] {e}")

    return {
        "ok": True,
        "farmer_id": farmer_id_str,
        "email": req.email,
        "name": req.name,
        "crop": req.crop,
        "state": req.state,
        "village_code": req.village_code,
        "otp_sent": True,
        "database": "supabase_postgresql",
        "message": f"Verification code sent to {req.email}. Profile created live in Supabase PostgreSQL.",
    }


@router.post("/verify-otp")
async def verify_otp(req: VerifyOTPRequest):
    """Verify 6-digit Email OTP via Supabase Auth."""
    db = get_supabase()
    db_service = get_service_supabase()

    try:
        res = db.auth.verify_otp({"email": req.email, "token": req.token, "type": "email"})
        user = res.user
        session = res.session
    except Exception as ex:
        # Fallback ONLY in development environment
        if os.getenv("APP_ENV") == "development" and req.token in ("123456", "000000"):
            return {
                "ok": True,
                "verified": True,
                "email": req.email,
                "message": "OTP verified successfully (development bypass).",
            }
        raise HTTPException(status_code=400, detail=f"Invalid OTP code: {str(ex)}")

    # Fetch farmer profile from Supabase
    f_res = db_service.table("farmers").select("*").eq("id", user.id if user else "").maybe_single().execute()
    profile = f_res.data if f_res else None

    return {
        "ok": True,
        "verified": True,
        "access_token": session.access_token if session else None,
        "user_id": user.id if user else None,
        "profile": profile,
        "message": "Successfully signed in via Supabase Auth.",
    }


@router.post("/login")
async def login_farmer(req: LoginRequest):
    """
    Sign in an existing farmer via Email OTP or Password.
    """
    db_service = get_service_supabase()
    db_anon = get_supabase()

    if req.password:
        try:
            res = db_anon.auth.sign_in_with_password({"email": req.email, "password": req.password})
            user_id = res.user.id if res.user else None
            # Fetch profile
            farmer = db_service.table("farmers").select("*").eq("id", user_id).maybe_single().execute().data
            return {"ok": True, "user": res.user, "farmer": farmer, "message": "Signed in successfully."}
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")

    # Default: Trigger fresh Email OTP to user
    try:
        db_anon.auth.sign_in_with_otp({"email": req.email})
    except Exception as e:
        print(f"[AUTH LOGIN NOTICE] {e}")

    # Fetch existing profile from Supabase filtered strictly by email
    matching_farmer = None
    try:
        res_farmer = db_service.table("farmers").select("*").eq("email", req.email).limit(1).execute()
        if res_farmer.data:
            matching_farmer = res_farmer.data[0]
    except Exception as e:
        print(f"[AUTH LOGIN QUERY NOTICE] {e}")

    return {
        "ok": True,
        "email": req.email,
        "otp_sent": True,
        "farmer": matching_farmer,
        "message": f"Verification code sent to {req.email}. Check your inbox.",
    }
