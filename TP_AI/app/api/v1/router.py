from fastapi import APIRouter
from app.api.v1.endpoints import travel, ai

api_router = APIRouter()

api_router.include_router(ai.router, prefix="/ai", tags=["AI Engine (Schedule & Reschedule)"])
api_router.include_router(travel.router, prefix="/travel", tags=["Travel Recommendation & Spots"])

