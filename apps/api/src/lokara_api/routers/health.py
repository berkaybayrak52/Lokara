from datetime import UTC, datetime

from fastapi import APIRouter

from ..schemas import HealthResponse

router = APIRouter()


@router.get("/health")
def health() -> HealthResponse:
    return HealthResponse(
        status="ok", service="lokara-api", timestamp=datetime.now(UTC).isoformat()
    )
