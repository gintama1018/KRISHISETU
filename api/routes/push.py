"""
KrishiSetu — Web Push Notification Routes
Layer 0: Real-time offline-capable push via VAPID (free, no third-party service)
"""
import os
import json
import asyncio
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from pywebpush import webpush, WebPushException
from db.supabase_client import get_service_supabase

router = APIRouter()

VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_PUBLIC_KEY  = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_EMAIL       = os.getenv("VAPID_CLAIMS_EMAIL", "admin@krishisetu.in")


# ── Models ─────────────────────────────────────────────────────────────────

class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscription(BaseModel):
    endpoint: str
    keys: PushSubscriptionKeys
    farmer_id: Optional[str] = None
    village_code: Optional[str] = None


class PushPayload(BaseModel):
    title: str
    body: str
    url: str = "/advisory.html"
    icon: str = "/icons/icon-192.png"
    badge: str = "/icons/icon-72.png"
    tag: str = "krishisetu-alert"
    vibrate: list = [200, 100, 200]


class TriggerPushRequest(BaseModel):
    farmer_id: Optional[str] = None
    village_code: Optional[str] = None   # broadcast to whole village
    title: str
    body: str
    url: str = "/advisory.html"


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/vapid-public-key")
async def get_vapid_public_key():
    """Return VAPID public key for frontend subscription."""
    if not VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=500, detail="VAPID keys not configured")
    return {"publicKey": VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe_push(sub: PushSubscription):
    """
    Store a Web Push subscription in Supabase.
    Called by the frontend after the user grants notification permission.
    """
    db = get_service_supabase()
    data = {
        "endpoint": sub.endpoint,
        "p256dh": sub.keys.p256dh,
        "auth": sub.keys.auth,
        "farmer_id": sub.farmer_id,
        "village_code": sub.village_code,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    # Upsert by endpoint (one device = one subscription)
    result = db.table("push_subscriptions").upsert(
        data, on_conflict="endpoint"
    ).execute()

    return {"ok": True, "message": "Push subscription saved. You will receive risk alerts."}


@router.post("/unsubscribe")
async def unsubscribe_push(endpoint: str):
    """Remove a push subscription (e.g., on sign-out)."""
    db = get_service_supabase()
    db.table("push_subscriptions").delete().eq("endpoint", endpoint).execute()
    return {"ok": True}


@router.post("/trigger")
async def trigger_push_notification(
    req: TriggerPushRequest,
    background_tasks: BackgroundTasks,
):
    """
    Internal endpoint: send push notification to farmer(s).
    Can target a single farmer_id or broadcast to an entire village_code.
    Called automatically by advisory pipeline on high-risk detection.
    """
    db = get_service_supabase()

    # Fetch matching subscriptions
    query = db.table("push_subscriptions").select("*")
    if req.farmer_id:
        query = query.eq("farmer_id", req.farmer_id)
    elif req.village_code:
        query = query.eq("village_code", req.village_code)

    subs = query.execute().data or []

    if not subs:
        return {"ok": True, "sent": 0, "message": "No subscriptions found for target."}

    payload = json.dumps({
        "title": req.title,
        "body": req.body,
        "url": req.url,
        "icon": "/icons/icon-192.png",
        "badge": "/icons/icon-72.png",
        "tag": "krishisetu-risk-alert",
        "vibrate": [200, 100, 200, 100, 200],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    background_tasks.add_task(_send_to_all, subs, payload)
    return {"ok": True, "sent": len(subs), "message": f"Push queued for {len(subs)} device(s)."}


# ── Internal helpers ───────────────────────────────────────────────────────

async def _send_to_all(subscriptions: list, payload: str):
    """Send push to all subscriptions, removing expired ones."""
    db = get_service_supabase()
    dead_endpoints = []

    for sub in subscriptions:
        try:
            subscription_info = {
                "endpoint": sub["endpoint"],
                "keys": {
                    "p256dh": sub["p256dh"],
                    "auth": sub["auth"],
                },
            }
            webpush(
                subscription_info=subscription_info,
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{VAPID_EMAIL}"},
            )
        except WebPushException as ex:
            # 410 Gone = subscription expired / user revoked permission
            if ex.response and ex.response.status_code in (404, 410):
                dead_endpoints.append(sub["endpoint"])

    # Clean up dead subscriptions
    if dead_endpoints:
        for ep in dead_endpoints:
            db.table("push_subscriptions").delete().eq("endpoint", ep).execute()


async def send_risk_alert(farmer_id: str, crop: str, drought: int, pest: int):
    """
    Convenience function called by the advisory pipeline.
    Sends a native push notification when drought > 60 OR pest > 70.
    """
    alerts = []
    if drought > 60:
        alerts.append(f"Drought {drought}%")
    if pest > 70:
        alerts.append(f"Pest Risk {pest}%")
    if not alerts:
        return

    alert_str = " · ".join(alerts)
    db = get_service_supabase()
    subs = db.table("push_subscriptions").select("*").eq("farmer_id", farmer_id).execute().data or []
    if not subs:
        return

    payload = json.dumps({
        "title": f"⚠️ KrishiSetu Risk Alert",
        "body": f"{alert_str} detected for your {crop.title()} crop. Tap for advisory.",
        "url": "/advisory.html",
        "icon": "/icons/icon-192.png",
        "badge": "/icons/icon-72.png",
        "tag": "krishisetu-risk-alert",
        "vibrate": [300, 100, 300, 100, 300],
    })
    await _send_to_all(subs, payload)
