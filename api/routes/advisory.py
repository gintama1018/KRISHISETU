"""
KrishiSetu — API Routes: AI Advisory (full pipeline)
"""
from fastapi import APIRouter, Body
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from stream.stream import process_record
from advisory.gemini_advisor import generate_advisory
from models.sowing import evaluate_sowing_window
from ingestion.mandi_feed import get_mandi_prices

router = APIRouter()


class AdvisoryRequest(BaseModel):
    farmer_id: Optional[str] = None
    village_code: Optional[str] = None
    crop: str = "rice"
    lat: float = 26.14
    lon: float = 91.74
    language: str = "English"
    # Weather inputs (if not fetching live)
    precip_30d_mm: float = 60.0
    precip_7d_mm: float = 15.0
    avg_temp_c: float = 28.0
    max_temp_c: float = 33.0
    avg_humidity_pct: float = 65.0
    consecutive_humid_days: int = 3
    recent_rain_events: int = 2
    soil_moisture_pct: Optional[float] = None
    state: Optional[str] = "Assam"


@router.post("/generate")
async def generate_full_advisory(req: AdvisoryRequest):
    """
    Full advisory pipeline:
    1. Run streaming engine (normalize → risk score)
    2. Evaluate sowing window
    3. Fetch mandi price
    4. Generate Gemini advisory
    """
    raw_record = req.model_dump()

    # Step 1: Streaming pipeline — normalize + score risks
    scored = await process_record(raw_record)
    drought = scored["risk"]["drought"]
    pest = scored["risk"]["pest"]

    # Step 2: Sowing window
    sowing = evaluate_sowing_window(
        crop=req.crop,
        avg_temp_c=req.avg_temp_c,
        precip_7d_mm=req.precip_7d_mm,
        avg_humidity_pct=req.avg_humidity_pct,
    )

    # Step 3: Mandi price
    mandi_data = await get_mandi_prices(req.crop, state=req.state, limit=3)
    if mandi_data["prices"]:
        p = mandi_data["prices"][0]
        mandi_str = f"₹{p.get('Modal_x0020_Price', 'N/A')}/quintal at {p.get('Market', 'local market')}"
    else:
        mandi_str = "Not available"

    # Step 4: Gemini advisory
    advisory = await generate_advisory(
        crop=req.crop,
        drought_score=drought["score"],
        drought_level=drought["level"],
        pest_score=pest["score"],
        pest_level=pest["level"],
        sowing_rec=sowing["recommendation"],
        max_temp=req.max_temp_c,
        precip_30d=req.precip_30d_mm,
        humidity=req.avg_humidity_pct,
        language=req.language,
        month=datetime.now().strftime("%B"),
        mandi_price=mandi_str,
    )

    return {
        "farmer_id": req.farmer_id,
        "crop": req.crop,
        "language": req.language,
        "risk": scored["risk"],
        "sowing": sowing,
        "mandi": mandi_data,
        "advisory": advisory["advisory"],
        "cached": advisory["cached"],
        "pipeline": ["normalize", "risk_score", "sowing_eval", "mandi_fetch", "gemini_advisory"],
    }


class TTSRequest(BaseModel):
    text: str
    language: str = "English"


@router.post("/tts")
async def text_to_speech(req: TTSRequest):
    """Generate TTS audio (MP3) for advisory text via ElevenLabs."""
    from fastapi.responses import Response
    from language.translate import generate_tts_audio, translate_text
    translated = await translate_text(req.text[:500], req.language)
    audio = await generate_tts_audio(translated, req.language)
    if audio:
        return Response(content=audio, media_type="audio/mpeg")
    from fastapi import HTTPException
    raise HTTPException(status_code=503, detail="TTS not configured — add ELEVENLABS_API_KEY to .env")


@router.get("/alerts")
async def get_recent_alerts(limit: int = 20):
    """Get the most recent alerts emitted by the streaming engine."""
    from stream.stream import get_alert_emitter
    emitter = get_alert_emitter()
    return {"alerts": emitter.get_recent_alerts(limit=limit)}
