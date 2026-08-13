"""
Vercel Serverless Entry Point for KrishiSetu FastAPI Backend
"""
import sys
import os
from pathlib import Path

# Add project root to Python path so main.py and modules import cleanly
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from main import app
