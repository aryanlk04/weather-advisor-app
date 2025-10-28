import requests
import streamlit as st

# Secure API key from Streamlit Secrets
API_KEY = st.secrets["OPENWEATHER_API_KEY"]

def get_weather(city):
    """
    Fetch weather data from OpenWeatherMap API for the given city.
    Returns a dictionary with temperature, humidity, and condition.
    """
    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    try:
        response = requests.get(url)
        data = response.json()
        if "main" in data:
            temp = data["main"]["temp"]
            humidity = data["main"]["humidity"]
            condition = data["weather"][0]["description"]
            return {"temp": temp, "humidity": humidity, "condition": condition}
        else:
            return None
    except Exception as e:
        print("Error fetching weather:", e)
        return None

def health_advice(temp, humidity, condition):
    """
    Returns detailed health recommendations based on temperature, humidity, and weather.
    """
    advice = []

    # Temperature-based advice
    if temp >= 40:
        advice.append("🔥 Extreme heat! Stay indoors during peak hours, drink plenty of water, and apply sunscreen SPF 50+.")
        advice.append("🧢 Wear a wide-brim hat and light, breathable clothing.")
    elif 35 <= temp < 40:
        advice.append("☀️ Very hot: stay hydrated, avoid direct sunlight, use sunscreen SPF 30+.")
        advice.append("👕 Wear light-colored, loose clothing.")
    elif 30 <= temp < 35:
        advice.append("🌤 Hot weather: limit outdoor activity during midday, use sunscreen.")
    elif 20 <= temp < 30:
        advice.append("🌤 Moderate weather: normal precautions, stay hydrated.")
    elif 10 <= temp < 20:
        advice.append("🧥 Mild cold: wear a light jacket, keep skin moisturized.")
    elif temp < 10:
        advice.append("❄️ Cold weather: wear warm clothing, cover extremities, use moisturizer for skin protection.")
        advice.append("🧤 Gloves, scarf, and hat recommended.")

    # Humidity-based advice
    if humidity > 80:
        advice.append("💧 High humidity: stay hydrated, risk of fungal or skin irritation increases.")
    elif humidity < 30:
        advice.append("💨 Low humidity: apply moisturizer, drink plenty of water to avoid dehydration.")

    # Weather condition advice
    condition_lower = condition.lower()
    if any(word in condition_lower for word in ["smoke", "dust", "haze"]):
        advice.append("😷 Air pollution detected: wear N95 mask outdoors, avoid heavy outdoor exercise.")
    if "rain" in condition_lower:
        advice.append("☔ Carry an umbrella and wear waterproof shoes/clothes.")
    if "snow" in condition_lower:
        advice.append("❄️ Snowy conditions: wear warm waterproof clothing and boots, watch out for icy surfaces.")
    if "fog" in condition_lower:
        advice.append("🌫 Foggy weather: drive carefully, use lights if commuting.")
    if "thunderstorm" in condition_lower or "storm" in condition_lower:
        advice.append("⚡ Thunderstorm: stay indoors, avoid using electrical appliances outside.")
    if "wind" in condition_lower:
        advice.append("💨 Strong wind: secure loose objects and avoid outdoor activities if possible.")

    if not advice:
        advice.append("✅ Weather looks good! Maintain your usual health routine.")

    return advice
