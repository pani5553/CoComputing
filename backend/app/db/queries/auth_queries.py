"""
Database queries for authentication: providers and wallet creation.
All queries use the Supabase Python SDK — no raw string interpolation with user data.
"""
from typing import Any

from app.db.client import get_supabase


def get_provider_by_email(email: str) -> dict[str, Any] | None:
    """
    Fetch a provider row by email. Returns None if not found.

    Normalizes to lowercase here (defense in depth — EN-CRIT-01,
    docs/05-review.md 2026-07-09), not just at the Pydantic model layer
    (LoginRequest.email_normalize / RegisterRequest.email_format_strict).
    `providers.email` has no `citext`/`lower()` index, so any future caller
    of this function that bypasses request validation (a script, another
    service, a direct call) must not be able to reintroduce a
    case-sensitive lookup mismatch against a normalized-on-write column.
    """
    response = (
        get_supabase().table("providers")
        .select("*")
        .eq("email", email.lower())
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def get_provider_by_id(provider_id: str) -> dict[str, Any] | None:
    """Fetch a provider row by UUID. Returns None if not found."""
    response = (
        get_supabase().table("providers")
        .select("*")
        .eq("id", provider_id)
        .limit(1)
        .execute()
    )
    data = response.data
    if not data:
        return None
    return data[0]


def create_provider(
    email: str,
    full_name: str,
    password_hash: str,
) -> dict[str, Any]:
    """
    Insert a new provider row and return the created record.
    Raises an exception (propagated to the caller) if the email is duplicate.
    """
    response = (
        get_supabase().table("providers")
        .insert(
            {
                "email": email,
                "full_name": full_name,
                "password_hash": password_hash,
            }
        )
        .execute()
    )
    return response.data[0]


def create_wallet_for_provider(provider_id: str) -> dict[str, Any]:
    """
    Create the 1:1 wallet record for a newly registered provider.
    All balances start at 0.
    """
    response = (
        get_supabase().table("wallets")
        .insert({"provider_id": provider_id})
        .execute()
    )
    return response.data[0]
