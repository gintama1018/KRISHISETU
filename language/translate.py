"""
KrishiSetu — Multilingual Translation + TTS Layer
Layer 4: Language & Voice Output
"""
import os
import httpx
import asyncio
from typing import Optional


ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ELEVENLABS_URL = "https://api.elevenlabs.io/v1/text-to-speech"

# Supported languages
SUPPORTED_LANGUAGES = {
    "English":   "en",
    "Hindi":     "hi",
    "Bengali":   "bn",
    "Assamese":  "as",
    "Odia":      "or",
    "Tamil":     "ta",
    "Telugu":    "te",
    "Kannada":   "kn",
    "Marathi":   "mr",
    "Gujarati":  "gu",
    "Punjabi":   "pa",
}

# Phrase bank — common agri phrases pre-translated to avoid API calls
PHRASE_BANK = {
    "drought_alert": {
        "English":  "High drought risk detected. Please irrigate your fields.",
        "Hindi":    "उच्च सूखे का जोखिम पाया गया। कृपया अपने खेतों में सिंचाई करें।",
        "Bengali":  "উচ্চ খরার ঝুঁকি সনাক্ত হয়েছে। অনুগ্রহ করে আপনার ক্ষেতে সেচ দিন।",
        "Assamese": "উচ্চ খৰাং বিপদ চিনাক্ত কৰা হৈছে। অনুগ্ৰহ কৰি আপোনাৰ পথাৰত জলসিঞ্চন কৰক।",
        "Tamil":    "உயர் வறட்சி அபாயம் கண்டறியப்பட்டது. தயவுசெய்து உங்கள் வயல்களுக்கு நீர்ப்பாசனம் செய்யுங்கள்.",
        "Telugu":   "అధిక కరువు ప్రమాదం గుర్తించబడింది. దయచేసి మీ పొలాలకు నీరు పెట్టండి.",
        "Marathi":  "उच्च दुष्काळाचा धोका आढळला. कृपया आपल्या शेतांना सिंचन करा.",
        "Gujarati": "ઉચ્ચ દુષ્કાળ જોખમ મળ્યું. કૃપા કરીને તમારા ખેતરોમાં સિંચાઈ કરો.",
    },
    "pest_alert": {
        "English":  "Pest outbreak risk is high. Inspect your crops immediately.",
        "Hindi":    "कीट प्रकोप का जोखिम अधिक है। तुरंत अपनी फसल की जांच करें।",
        "Bengali":  "কীটপতঙ্গ প্রাদুর্ভাবের ঝুঁকি বেশি। অবিলম্বে আপনার ফসল পরীক্ষা করুন।",
        "Assamese": "পোক-পতংগৰ বিপদ বেছি। এতিয়াই আপোনাৰ শস্য পৰীক্ষা কৰক।",
        "Tamil":    "பூச்சி தொற்று அபாயம் அதிகமாக உள்ளது. உடனடியாக உங்கள் பயிர்களை ஆய்வு செய்யுங்கள்.",
        "Telugu":   "తెగులు వ్యాప్తి ప్రమాదం ఎక్కువగా ఉంది. వెంటనే మీ పంటలను తనిఖీ చేయండి.",
        "Marathi":  "कीटक प्रादुर्भावाचा धोका जास्त आहे. ताबडतोब आपल्या पिकांची तपासणी करा.",
        "Gujarati": "જીવાત ફાટી નીકળવાનું જોખમ વધારે છે. તરત જ તમારા પાકનું નિરીક્ષણ કરો.",
    },
    "good_conditions": {
        "English":  "Conditions are good for your crops. Continue regular monitoring.",
        "Hindi":    "आपकी फसल के लिए स्थितियाँ अच्छी हैं। नियमित निगरानी जारी रखें।",
        "Bengali":  "আপনার ফসলের জন্য পরিস্থিতি ভালো। নিয়মিত পর্যবেক্ষণ চালিয়ে যান।",
        "Assamese": "আপোনাৰ শস্যৰ বাবে পৰিস্থিতি ভালে। নিয়মীয়া পৰ্যবেক্ষণ অব্যাহত ৰাখক।",
        "Tamil":    "உங்கள் பயிர்களுக்கு நிலைமைகள் நல்லவையாக உள்ளன. தொடர்ந்து கண்காணிக்கவும்.",
        "Telugu":   "మీ పంటలకు పరిస్థితులు మంచిగా ఉన్నాయి. క్రమం తప్పకుండా పర్యవేక్షించండి.",
        "Marathi":  "आपल्या पिकांसाठी परिस्थिती चांगली आहे. नियमित देखरेख ठेवा.",
        "Gujarati": "તમારા પાક માટે પરિસ્થિતિ સારી છે. નિયમિત દેખરેખ ચાલુ રાખો.",
    },
}


def get_phrase(key: str, language: str = "English") -> str:
    """Get a pre-translated phrase from the phrase bank."""
    lang_phrases = PHRASE_BANK.get(key, {})
    return lang_phrases.get(language, lang_phrases.get("English", ""))


async def translate_text(text: str, target_language: str = "Hindi") -> str:
    """
    Translate text to target language.
    Primary: deep-translator (Google Translate wrapper, free).
    """
    if target_language == "English":
        return text
    lang_code = SUPPORTED_LANGUAGES.get(target_language, "hi")
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source="en", target=lang_code).translate(text)
        return translated or text
    except Exception:
        return text  # return original if translation fails


async def generate_tts_audio(text: str, language: str = "English") -> Optional[bytes]:
    """
    Generate speech audio using ElevenLabs TTS.
    Returns audio bytes (MP3) or None if API key not configured.
    """
    if not ELEVENLABS_API_KEY:
        return None

    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{ELEVENLABS_URL}/{ELEVENLABS_VOICE_ID}",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            return resp.content
    except Exception:
        return None
