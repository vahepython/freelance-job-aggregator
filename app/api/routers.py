from fastapi import APIRouter

from app.api.routes.oauth import oauth_router


api_router = APIRouter()
api_router.include_router(oauth_router)