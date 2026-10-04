"""Gemini configuration. Credentials stay outside the repository."""
import os
from google import genai

API_KEY = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
if not API_KEY:
    raise RuntimeError("Set GEMINI_API_KEY before running CLOAK; see README.md.")
client = genai.Client(api_key=API_KEY)

# Preserve the model identifiers from the supplied research artifact.
GEMINI_FLASH = os.environ.get("CLOAK_FLASH_MODEL", "gemini-2.5-flash")
GEMINI_PRO = os.environ.get("CLOAK_PRO_MODEL", "gemini-2.5-pro")
