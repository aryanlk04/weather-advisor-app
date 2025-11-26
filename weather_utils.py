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

def health_advice(temp_c: float, humidity: float, condition: str) -> list[str]:
    """
    Returns lifestyle & daily routine suggestions based on
    temperature (°C), humidity (%) and weather condition text.
    Focus: water intake, clothing, indoor/outdoor, activity.
    """
    advice = []

    # -------- Temperature-based lifestyle advice --------
    if temp_c is not None:
        if temp_c >= 35:
            advice.append(
                "It is very hot today. Drink at least 3–4 litres of water and avoid heavy outdoor work between 11 AM and 4 PM."
            )
            advice.append(
                "Wear light, loose, cotton clothes and prefer staying in shaded or cool areas."
            )
        elif 30 <= temp_c < 35:
            advice.append(
                "The temperature is quite warm. Keep a water bottle with you and sip water regularly."
            )
            advice.append(
                "Light cotton clothing is recommended. Take short breaks if you are outdoors for long."
            )
        elif 20 <= temp_c < 30:
            advice.append(
                "The temperature is comfortable. Maintain normal routine but stay hydrated through the day."
            )
        elif 15 <= temp_c < 20:
            advice.append(
                "It is slightly cool. Consider wearing a light jacket or full-sleeve clothing when going out."
            )
        elif 10 <= temp_c < 15:
            advice.append(
                "It is cold. Wear layered clothing and avoid being outdoors late at night."
            )
        elif temp_c < 10:
            advice.append(
                "Very cold conditions. Wear proper winter clothing, limit outdoor exposure and keep yourself warm."
            )

    # -------- Humidity-based lifestyle advice --------
    if humidity is not None:
        if humidity >= 80:
            advice.append(
                "Humidity is high. Avoid intense outdoor exercise; choose light activities and stay in ventilated places."
            )
            advice.append(
                "Wear breathable, loose clothing to stay comfortable in the humid weather."
            )
        elif 60 <= humidity < 80:
            advice.append(
                "Humidity is moderately high. Take breaks if you feel exhausted and keep drinking water."
            )
        elif 30 <= humidity < 60:
            advice.append(
                "Humidity is in a comfortable range. You can follow your normal routine."
            )
        elif humidity < 30:
            advice.append(
                "Air is quite dry. Your skin and throat may feel dry, so drink enough water and consider using a moisturizer or lip balm."
            )

    # -------- Condition-based lifestyle advice --------
    cond = (condition or "").lower()

    if "rain" in cond or "drizzle" in cond:
        advice.append(
            "Carry an umbrella or raincoat and avoid walking through stagnant water."
        )
        advice.append(
            "Prefer indoor plans if there is heavy rain, and be careful while traveling."
        )

    if "thunder" in cond or "storm" in cond:
        advice.append(
            "Avoid outdoor activities during thunder or storms. Stay indoors and unplug sensitive electronics if possible."
        )

    if "clear" in cond or "sun" in cond:
        advice.append(
            "It is sunny. If you go out for a long time, use sunscreen (SPF 30+), sunglasses and a cap."
        )

    if "cloud" in cond or "overcast" in cond:
        advice.append(
            "Sky is cloudy. Weather may feel cooler; carrying a light jacket can be helpful, especially in the evening."
        )

    if "fog" in cond or "mist" in cond:
        advice.append(
            "Visibility is low due to fog/mist. Be cautious while driving and avoid late-night travel if possible."
        )

    if "dust" in cond or "smoke" in cond or "haze" in cond:
        advice.append(
            "Air quality may be poor. If you have asthma or allergies, limit outdoor time and consider using a mask."
        )

    # -------- General lifestyle suggestions --------
    # (Shown always)
    advice.append(
        "Plan your outdoor work or travel during early morning or evening when the weather is usually more comfortable."
    )
    advice.append(
        "Listen to your body — if you feel dizzy, very tired, or breathless, take rest and move to a more comfortable environment."
    )

    # Remove duplicates just in case
    unique_advice = []
    for a in advice:
        if a not in unique_advice:
            unique_advice.append(a)

    return unique_advice

