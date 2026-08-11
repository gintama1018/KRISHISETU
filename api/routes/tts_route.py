"""
KrishiSetu — TTS API route (add to advisory router)
"""
from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel
from language.translate import generate_tts_audio, translate_text

# This is included in advisory.py router
tts_router = APIRouter()

class TTSRequest(BaseModel):
    text: str
    language: str = "English"

async def tts_endpoint(req: TTSRequest):
    """Generate TTS audio for advisory text."""
    translated = await translate_text(req.text, req.language)
    audio = await generate_tts_audio(translated, req.language)
    if audio:
        return Response(content=audio, media_type="audio/mpeg")
    return Response(status_code=503, content=b"TTS not configured")
