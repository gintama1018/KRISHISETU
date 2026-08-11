"""
KrishiSetu — AI Advisory Generator
Layer 3: AI Advisory (Supports OpenAI GPT-4o-mini / Gemini 2.5 Flash / Fallback)
"""
import os
import hashlib
import threading
import httpx
from typing import Optional

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


async def _generate_openai(prompt: str, api_key: str) -> str:
    """Generate advisory using OpenAI chat completions endpoint."""
    async with httpx.AsyncClient(timeout=25) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are KrishiSetu, an AI agricultural advisor for Indian farmers."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 400,
            },
        )
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()


async def _generate_gemini(prompt: str, api_key: str) -> str:
    """Generate advisory using Gemini API."""
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text.strip()


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
    """Generate AI advisory using OpenAI, Gemini, or Agronomic Fallback."""

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

    advisory_text = None
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()

    # Priority 1: OpenAI (if key starts with sk-)
    if openai_key and openai_key.startswith("sk-"):
        try:
            advisory_text = await _generate_openai(prompt, openai_key)
        except Exception as e:
            print(f"[Advisory] OpenAI error: {e}")

    # Priority 2: Gemini (skip if placeholder key)
    is_placeholder = "your_" in gemini_key.lower() or "here" in gemini_key.lower() or gemini_key == "AIzaSy..."
    if not advisory_text and gemini_key and not is_placeholder:
        try:
            advisory_text = await _generate_gemini(prompt, gemini_key)
        except Exception as e:
            print(f"[Advisory] Gemini error: {e}")

    # Priority 3: Agronomic Fallback
    if not advisory_text:
        advisory_text = _fallback_advisory(crop, drought_level, pest_level, language)

    result = {
        "crop": crop,
        "language": language,
        "advisory": advisory_text,
        "cached": False,
    }

    with _cache_lock:
        _cache[cache_key] = result

    return result


def _fallback_advisory(crop: str, drought_level: str, pest_level: str, language: str) -> str:
    """Farmer-friendly fallback advisory when no API key is provided."""
    c = crop.upper()
    return f"""⚠️ MAIN ALERT: {drought_level} drought risk and {pest_level} pest threat detected for your {c} crop.

💧 IRRIGATION: Maintain optimal soil moisture. Avoid waterlogging during high humidity.

🌱 CROP ACTION: Apply recommended N-P-K fertilizer based on current growth phase. Inspect leaf undersides daily.

🐛 PEST WATCH: Watch for stem borers and aphids. Use neem oil spray if early infestation is spotted.

📅 THIS WEEK'S PRIORITY: Clear field drainage channels before unexpected rainfall events.

💰 MARKET TIP: Mandi prices are stable to rising. Consider holding stock if storage facilities permit."""
