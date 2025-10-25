import requests

# Replace with your actual OpenWeatherMap API key
API_KEY = "e46cdf714dc3460e0f4e3315c7a5c6d4"

def get_weather(city):
    """
    Fetch weather data from OpenWeatherMap API for the given city.
    Returns a dictionary with temperature, humidity, and condition.
    Returns None if the city is invalid or API fails.
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
            # API returned error (like city not found)
            return None
    except Exception as e:
        print("Error fetching weather:", e)
        return None

def weather_suggestion(temp, humidity):
    """
    Returns a list of suggestions based on temperature and humidity.
    """
    suggestions = []
    if temp > 30:
        suggestions.append("🔥 Temperature is high! Stay hydrated and avoid direct sunlight.")
    elif temp < 10:
        suggestions.append("❄️ Temperature is low! Wear warm clothes.")
    
    if humidity > 80:
        suggestions.append("💧 High humidity detected! Stay cool and hydrated.")
    elif humidity < 30:
        suggestions.append("💨 Low humidity! Consider using moisturizer or staying hydrated.")

    if not suggestions:
        suggestions.append("Weather looks normal. Have a nice day! ☀️")
    
    return suggestions