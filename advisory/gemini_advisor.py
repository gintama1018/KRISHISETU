"""
KrishiSetu — Gemini AI Advisory Generator
Layer 3: AI Advisory (Gemini 2.5 Flash)
"""
import os
import hashlib
import threading
from typing import Optional
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))

_cache: dict = {}
_cache_lock = threading.Lock()


ADVISORY_PROMPT_TEMPLATE = """
You are KrishiSetu, an expert AI agricultural advisor for Indian farmers.
Respond ONLY in {language}. Be concise, practical, and farmer-friendly.
Use simple words. Avoid technical jargon.

FARMER CONTEXT:
- Crop: {crop}
- Location: {location}
- Current Month: {month}

RISK SCORES (0-100, higher = worse):
- Drought Risk: {drought_score}/100 ({drought_level})
- Pest Risk: {pest_score}/100 ({pest_level})
- Sowing Recommendation: {sowing_rec}

WEATHER SUMMARY:
- Max Temperature: {max_temp}°C
- Last 30-day Rainfall: {precip_30d}mm
- Humidity: {humidity}%

MARKET INFO:
- Current Mandi Price: {mandi_price}

Generate a structured advisory with:
1. ⚠️ Main Alert (1-2 sentences on the biggest risk right now)
2. 💧 Irrigation Advice (what to do with water)
3. 🌱 Crop Action (immediate steps for the crop)
4. 🐛 Pest Watch (what to look for, if risk is moderate or higher)
5. 📅 This Week's Priority (one clear action the farmer should do first)
6. 💰 Market Tip (based on current mandi price trend)

Keep total response under 200 words.
"""


async def generate_advisory(
    crop: str,
    drought_score: int,
    drought_level: str,
    pest_score: int,
    pest_level: str,
    sowing_rec: str,
    max_temp: float,
    precip_30d: float,
    humidity: float,
    location: str = "India",
    language: str = "English",
    month: str = "",
    mandi_price: str = "Not available",
) -> dict:
    """Generate a Gemini 2.5 Flash advisory for a farmer."""

    cache_key = hashlib.md5(
        f"{crop}{drought_score}{pest_score}{sowing_rec}{language}{month}".encode()
    ).hexdigest()

    with _cache_lock:
        if cache_key in _cache:
            return {**_cache[cache_key], "cached": True}

    prompt = ADVISORY_PROMPT_TEMPLATE.format(
        language=language,
        crop=crop,
        location=location,
        month=month or "Current month",
        drought_score=drought_score,
        drought_level=drought_level,
        pest_score=pest_score,
        pest_level=pest_level,
        sowing_rec=sowing_rec,
        max_temp=max_temp,
        precip_30d=precip_30d,
        humidity=humidity,
        mandi_price=mandi_price,
    )

    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        advisory_text = response.text.strip()
    except Exception as e:
        advisory_text = _fallback_advisory(crop, drought_level, pest_level, language)

    result = {
        "crop": crop,
        "language": language,
        "advisory": advisory_text,
        "risk_summary": {
            "drought": {"score": drought_score, "level": drought_level},
            "pest": {"score": pest_score, "level": pest_level},
            "sowing": sowing_rec,
        },
        "cached": False,
    }

    with _cache_lock:
        _cache[cache_key] = result

    return result


def _fallback_advisory(crop: str, drought_level: str, pest_level: str, language: str) -> str:
    """Offline fallback advisory when Gemini API is unavailable."""
    advisories = {
        "English": f"⚠️ {crop.title()} Advisory: Drought risk is {drought_level}, pest risk is {pest_level}. "
                   "Monitor your fields closely, ensure adequate irrigation, and check for pest signs. "
                   "Contact your local Krishi Vigyan Kendra for guidance.",
        "Hindi": f"⚠️ {crop.title()} सलाह: सूखे का जोखिम {drought_level} है, कीट जोखिम {pest_level} है। "
                 "अपने खेतों की निगरानी करें और सिंचाई सुनिश्चित करें।",
        "Bengali": f"⚠️ {crop.title()} পরামর্শ: খরার ঝুঁকি {drought_level}, কীটপতঙ্গের ঝুঁকি {pest_level}। "
                   "আপনার মাঠ পর্যবেক্ষণ করুন।",
        "Assamese": f"⚠️ {crop.title()} পৰামৰ্শ: খৰাং বিপদ {drought_level}, পোক বিপদ {pest_level}। "
                    "আপোনাৰ পথাৰ চোৱাচিতি কৰক।",
    }
    return advisories.get(language, advisories["English"])
