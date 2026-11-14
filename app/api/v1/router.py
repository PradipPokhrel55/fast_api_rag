from fastapi import APIRouter

from app.api.v1.endpoints import bookings, chat, ingestion

api_router = APIRouter()
api_router.include_router(ingestion.router)
api_router.include_router(chat.router)
api_router.include_router(bookings.router)
