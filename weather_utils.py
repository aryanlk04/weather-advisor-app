import requests
import streamlit as st

# Read OpenWeatherMap API key from secrets
API_KEY = st.secrets["OPENWEATHER_API_KEY"]

def get_weather(city):
    """
    Returns dict: { temp: float, humidity: int, condition: str } or None on error.
    """
    url = f"http://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": API_KEY, "units": "metric"}
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        if "main" in data:
            return {
                "temp": float(data["main"]["temp"]),
                "humidity": int(data["main"]["humidity"]),
                "condition": data["weather"][0]["description"],
            }
        else:
            return None
    except Exception as e:
        print("Weather fetch error:", e)
        return None


def health_advice(temp, humidity, condition):
    """Return list of actionable health tips based on weather."""
    advice = []

    # Temperature guidance
    if temp >= 40:
        advice += [
            "🔥 Extreme heat: stay indoors during peak hours, drink plenty of water, and apply sunscreen SPF 50+.",
            "🧢 Wear a wide-brim hat and light, breathable clothing; avoid strenuous outdoor activity."
        ]
    elif 35 <= temp < 40:
        advice += [
            "☀️ Very hot: stay hydrated, avoid direct sunlight, apply sunscreen SPF 30+.",
            "👕 Wear light-colored, loose clothing."
        ]
    elif 30 <= temp < 35:
        advice.append("🌤 Hot: limit outdoor activity during midday and stay hydrated.")
    elif 20 <= temp < 30:
        advice.append("🌤 Comfortable: follow usual precautions and stay active.")
    elif 10 <= temp < 20:
        advice.append("🧥 Mild cold: wear layers and keep skin moisturized.")
    else:
        advice += [
            "❄️ Cold: wear warm clothing, cover extremities, and use moisturizer to avoid dryness.",
            "🧤 Wear gloves and hat in very low temperatures."
        ]

    # Humidity guidance
    if humidity > 80:
        advice.append("💧 High humidity: risk of fungal/skin irritation increases — keep skin dry and clean.")
    elif humidity < 30:
        advice.append("💨 Low humidity: use moisturizer and drink more water to prevent dehydration/dry skin.")

    # Condition-based recommendations
    c = (condition or "").lower()
    if any(x in c for x in ["smoke", "dust", "haze", "sand"]):
        advice.append("😷 Air pollution/dust: wear an N95 mask outdoors and avoid heavy exercise outside.")
    if "rain" in c:
        advice.append("☔ Rain: carry an umbrella and wear water-resistant shoes.")
    if "snow" in c:
        advice.append("❄️ Snow/Ice: wear warm waterproof clothing and watch for slippery surfaces.")
    if "fog" in c:
        advice.append("🌫 Fog: drive carefully and use lights when commuting.")
    if "thunder" in c or "storm" in c:
        advice.append("⚡ Thunderstorms: stay indoors and avoid tall exposed objects.")
    if "wind" in c:
        advice.append("💨 Strong wind: secure loose objects and take care in outdoor activities.")

    if not advice:
        advice.append("✅ Weather looks normal — continue your routine and take basic precautions.")

    return advice
