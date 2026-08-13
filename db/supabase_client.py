"""
KrishiSetu — Supabase Client Singleton
Layer 6: Real Database (replaces SQLite)
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

_client: Client | None = None
_service_client: Client | None = None


def get_supabase() -> Client:
    """Anon client — safe for reads, RLS-protected writes."""
    global _client
    if _client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in .env")
        _client = create_client(url, key)
    return _client


def get_service_supabase() -> Client:
    """Service-role client — bypasses RLS, backend only."""
    global _service_client
    if _service_client is None:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        _service_client = create_client(url, key)
    return _service_client
