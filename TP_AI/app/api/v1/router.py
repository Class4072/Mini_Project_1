from fastapi import APIRouter
from app.api.v1.endpoints import travel

api_router = APIRouter()

api_router.include_router(travel.router, prefix="/travel", tags=["Travel Recommendation & Spots"])
