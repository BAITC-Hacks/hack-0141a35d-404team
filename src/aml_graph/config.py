"""Server-only, reloadable configuration. Never return keys through the API."""
import os
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


def settings(root=None):
    root = Path(root) if root is not None else ROOT
    # Environment wins (including an explicit empty key to disable AI).
    # Reading on demand lets a local .env edit take effect without a restart.
    # Windows editors may save UTF-8 with a BOM. A template is not a secret source.
    values = {**dotenv_values(root / '.env', encoding='utf-8-sig'), **os.environ}
    return {
        'api_key': (values.get('OPENAI_API_KEY') or '').strip(),
        'model': (values.get('OPENAI_MODEL') or '').strip() or 'gpt-5.4-nano',
    }
