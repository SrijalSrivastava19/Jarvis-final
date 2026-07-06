import re


class IntentService:
    def detect_intent(self, text: str):
        """
        Detect user intent and extract basic parameters.
        Returns:
        {
            "intent": "...",
            "city": "...",
            "category": "..."
        }
        """

        text = text.lower().strip()

        # -------------------------
        # WEATHER
        # -------------------------
        weather_keywords = [
            "weather",
            "temperature",
            "humidity",
            "rain",
            "forecast",
            "climate",
            "wind"
        ]

        if any(word in text for word in weather_keywords):
            city = None

            match = re.search(r"in ([a-zA-Z ]+)", text)
            if match:
                city = match.group(1).strip().title()

            return {
                "intent": "weather",
                "city": city
            }

        # -------------------------
        # NEWS
        # -------------------------
        news_categories = [
            "sports",
            "business",
            "science",
            "technology",
            "health",
            "world",
            "top"
        ]

        if "news" in text or "headline" in text:

            category = "top"

            for cat in news_categories:
                if cat in text:
                    category = cat
                    break

            return {
                "intent": "news",
                "category": category
            }

        # -------------------------
        # DEFAULT
        # -------------------------
        return {
            "intent": "chat"
        }


intent_service = IntentService()
