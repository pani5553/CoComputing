"""
Profile router: stats, hardware update, online toggle, name update.
"""
from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_provider
from app.db.queries.profile_queries import (
    get_provider_by_id,
    toggle_online,
    update_hardware,
    update_name,
)
from app.models.profile import (
    HardwareInfo,
    HardwareUpdate,
    HardwareUpdateResponse,
    NameUpdateRequest,
    NameUpdateResponse,
    OnlineToggleRequest,
    OnlineToggleResponse,
    ProviderProfileResponse,
    RankInfo,
    TrustScoreDetail,
)
from app.services.trust_score import build_rank_info

router = APIRouter()


@router.get("/stats", response_model=ProviderProfileResponse)
def get_stats(
    current_provider: dict = Depends(get_current_provider),
) -> ProviderProfileResponse:
    """
    Return the full provider profile including Trust Score breakdown,
    rank info with points to next rank, and hardware specs.
    """
    provider_id: str = current_provider["id"]
    provider = get_provider_by_id(provider_id)

    trust_detail = TrustScoreDetail(
        completion_rate=float(provider["completion_rate"]),
        accuracy=float(provider["accuracy"]),
        response_time_score=float(provider["response_time_score"]),
        client_rating=float(provider["client_rating"]),
    )

    rank_info_data = build_rank_info(float(provider["trust_score"]), provider["rank"])
    rank_info = RankInfo(**rank_info_data)

    hardware = HardwareInfo(
        cpu_model=provider.get("cpu_model"),
        gpu_model=provider.get("gpu_model"),
        ram_gb=provider.get("ram_gb"),
        storage_gb=provider.get("storage_gb"),
    )

    return ProviderProfileResponse(
        id=provider["id"],
        full_name=provider["full_name"],
        email=provider["email"],
        trust_score=float(provider["trust_score"]),
        rank=provider["rank"],
        tasks_completed=provider["tasks_completed"],
        success_rate=float(provider["success_rate"]),
        total_earned=float(provider["total_earned"]),
        is_online=provider["is_online"],
        created_at=provider["created_at"],
        trust_score_detail=trust_detail,
        rank_info=rank_info,
        hardware=hardware,
    )


@router.put("/hardware", response_model=HardwareUpdateResponse)
def update_hardware_endpoint(
    payload: HardwareUpdate,
    current_provider: dict = Depends(get_current_provider),
) -> HardwareUpdateResponse:
    """Update the hardware specifications of the authenticated provider."""
    provider_id: str = current_provider["id"]
    updated = update_hardware(
        provider_id=provider_id,
        cpu_model=payload.cpu_model,
        gpu_model=payload.gpu_model,
        ram_gb=payload.ram_gb,
        storage_gb=payload.storage_gb,
    )
    return HardwareUpdateResponse(
        cpu_model=updated["cpu_model"],
        gpu_model=updated["gpu_model"],
        ram_gb=updated["ram_gb"],
        storage_gb=updated["storage_gb"],
        updated_at=updated["updated_at"],
    )


@router.patch("/online", response_model=OnlineToggleResponse)
def toggle_online_endpoint(
    payload: OnlineToggleRequest,
    current_provider: dict = Depends(get_current_provider),
) -> OnlineToggleResponse:
    """Toggle the online status of the authenticated provider."""
    provider_id: str = current_provider["id"]
    updated = toggle_online(provider_id, payload.is_online)
    return OnlineToggleResponse(
        is_online=updated["is_online"],
        updated_at=updated["updated_at"],
    )


@router.patch("/name", response_model=NameUpdateResponse)
def update_name_endpoint(
    payload: NameUpdateRequest,
    current_provider: dict = Depends(get_current_provider),
) -> NameUpdateResponse:
    """Update the full name of the authenticated provider."""
    provider_id: str = current_provider["id"]
    updated = update_name(provider_id, payload.full_name)
    return NameUpdateResponse(
        full_name=updated["full_name"],
        updated_at=updated["updated_at"],
    )
