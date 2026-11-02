from functools import lru_cache

from supabase import Client, create_client

from .config import settings


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Returns the shared Supabase client, creating it on first use rather than at import."""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )
