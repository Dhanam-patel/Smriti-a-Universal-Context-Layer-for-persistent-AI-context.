import os
import sys
from pathlib import Path

# app.db creates a Supabase client at import time, so the settings must exist first.
os.environ.setdefault("SUPABASE_URL", "https://example.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
