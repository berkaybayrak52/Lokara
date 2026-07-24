from fastapi import APIRouter, HTTPException

from ..auth import DEV_TOKEN_EXPIRES_IN_SECONDS, create_dev_token
from ..schemas import DevTokenResponse
from ..settings import ApiSettings

router = APIRouter(prefix="/auth")


@router.post("/dev-token")
def issue_dev_token() -> DevTokenResponse:
    """DEV ONLY — disabled unless AUTH_DEV_TOKEN=true. TODO(supabase): delete at M5."""
    settings = ApiSettings()
    if not settings.auth_dev_token:
        raise HTTPException(status_code=403, detail="Dev tokens are disabled")
    return DevTokenResponse(
        access_token=create_dev_token(settings.supabase_jwt_secret),
        expires_in_seconds=DEV_TOKEN_EXPIRES_IN_SECONDS,
    )
