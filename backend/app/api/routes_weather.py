from fastapi import APIRouter, HTTPException

from app.services.weather_service import weather_service

router = APIRouter(
    prefix="/weather",
    tags=["Weather"],
)

@router.get("/")
async def get_weather(city: str | None = None):
    try:
        return await weather_service.get_weather(city)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))