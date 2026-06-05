from functools import lru_cache

from supabase import Client, create_client

from app.core.config import settings


@lru_cache(maxsize=1)
def get_supabase_client() -> Client:
    """
    Return a singleton Supabase client initialized with the service_role key.
    The service_role key bypasses Row Level Security for backend operations.
    Initialization is deferred until first call (lazy singleton).
    """
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_supabase() -> Client:
    """Convenience accessor — same as get_supabase_client()."""
    return get_supabase_client()
