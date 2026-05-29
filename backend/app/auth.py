from fastapi import Request, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from supabase import create_client
from .config import get_settings

settings = get_settings()
supabase = create_client(settings.supabase_url, settings.supabase_service_role_key)

security = HTTPBearer()


# Supabase JWTs always carry aud="authenticated". python-jose 3.x raises
# JWTError("Invalid audience") when aud is present but no audience kwarg is
# passed. Suppress that check; we only need signature + expiry verification.
_JWT_OPTIONS = {"verify_aud": False}


async def validate_jwt(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(401, "Missing or invalid Authorization header")

    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token, settings.supabase_jwt_secret,
            algorithms=["HS256"], options=_JWT_OPTIONS,
        )
        request.state.user_id = payload["sub"]
    except JWTError as exc:
        raise HTTPException(401, f"Invalid token: {exc}")


async def optional_jwt(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        request.state.user_id = None
        return

    token = auth_header[7:]
    try:
        payload = jwt.decode(
            token, settings.supabase_jwt_secret,
            algorithms=["HS256"], options=_JWT_OPTIONS,
        )
        request.state.user_id = payload["sub"]
    except JWTError:
        request.state.user_id = None
