"""
Database queries for provider profile management.
"""
from typing import Any

from app.db.client import get_supabase


def get_provider_by_id(provider_id: str) -> dict[str, Any] | None:
    """Fetch full provider row by UUID. Returns None if not found."""
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


def update_provider(provider_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    """
    Generic update for provider fields.
    Returns the updated row.
    """
    response = (
        get_supabase().table("providers")
        .update(fields)
        .eq("id", provider_id)
        .execute()
    )
    return response.data[0]


def update_hardware(
    provider_id: str,
    cpu_model: str,
    gpu_model: str | None,
    ram_gb: int,
    storage_gb: int,
) -> dict[str, Any]:
    """Update hardware fields for a provider. Returns the updated row."""
    response = (
        get_supabase().table("providers")
        .update(
            {
                "cpu_model": cpu_model,
                "gpu_model": gpu_model,
                "ram_gb": ram_gb,
                "storage_gb": storage_gb,
            }
        )
        .eq("id", provider_id)
        .execute()
    )
    return response.data[0]


def toggle_online(provider_id: str, is_online: bool) -> dict[str, Any]:
    """Set the is_online status for a provider. Returns the updated row."""
    response = (
        get_supabase().table("providers")
        .update({"is_online": is_online})
        .eq("id", provider_id)
        .execute()
    )
    return response.data[0]


def update_name(provider_id: str, full_name: str) -> dict[str, Any]:
    """Update the full_name of a provider. Returns the updated row."""
    response = (
        get_supabase().table("providers")
        .update({"full_name": full_name})
        .eq("id", provider_id)
        .execute()
    )
    return response.data[0]
