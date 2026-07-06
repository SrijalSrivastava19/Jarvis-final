import httpx
from app.config import settings


class WeatherService:
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    async def get_weather(self, city: str | None = None):
        city = city or settings.default_city

        params = {
            "q": city,
            "appid": settings.openweather_api_key,
            "units": "metric",
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(self.BASE_URL, params=params)

        if response.status_code != 200:
            raise Exception(f"Weather API Error: {response.text}")

        data = response.json()

        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather": data["weather"][0]["main"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
        }


weather_service = WeatherService()