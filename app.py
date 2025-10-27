import streamlit as st
import sqlite3
import requests
import re
from datetime import datetime

# -------------------- DATABASE SETUP --------------------
conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                email TEXT,
                password TEXT
            )''')
conn.commit()

# -------------------- EMAIL VALIDATION --------------------
def validate_email(email):
    # Check for proper email structure
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return False

    # Block disposable domains
    disposable_domains = ["tempmail", "10minutemail", "guerrillamail", "yopmail"]
    if any(d in email.lower() for d in disposable_domains):
        return False

    # Allow only common valid domains
    valid_domains = ["gmail.com", "outlook.com", "yahoo.com", "hotmail.com", "icloud.com"]
    if not any(email.lower().endswith(domain) for domain in valid_domains):
        return False

    return True

# -------------------- USER AUTH FUNCTIONS --------------------
def signup_user(username, email, password):
    try:
        c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                  (username, email, password))
        conn.commit()
        return True
    except:
        return False

def login_user(username, password):
    c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    return c.fetchone()

# -------------------- WEATHER FETCH FUNCTION --------------------
def get_weather(city):
    api_key = st.secrets["OPENWEATHER_API_KEY"]
    base_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city, "appid": api_key, "units": "metric"}
    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        return None

# -------------------- HEALTH ADVICE --------------------
def health_advice(temp, humidity, air_quality):
    advice = []

    # Temperature advice
    if temp > 35:
        advice.append("🔥 It's extremely hot! Stay hydrated and avoid going out during peak sun hours.")
        advice.append("Use sunscreen (SPF 30+) and wear light cotton clothes.")
    elif temp > 25:
        advice.append("☀️ Warm weather! Drink plenty of water and wear breathable fabrics.")
    elif temp < 10:
        advice.append("❄️ It's quite cold! Dress warmly and keep your skin moisturized.")
    else:
        advice.append("🌤️ Mild temperature — great weather! Maintain regular hydration.")

    # Humidity advice
    if humidity > 80:
        advice.append("💧 High humidity detected — use an anti-fungal powder and stay in ventilated spaces.")
    elif humidity < 30:
        advice.append("🌵 Dry air — use moisturizer and stay hydrated to prevent dry skin and lips.")

    # Air Quality advice (simplified)
    if air_quality > 100:
        advice.append("😷 Poor air quality — consider wearing an N95 mask outdoors.")
    else:
        advice.append("🌬️ Air quality looks good today!")

    return advice

# -------------------- MAIN APP --------------------
st.set_page_config(page_title="Health Advisor", layout="centered")

st.title("🏥 Health Advisor App")

menu = ["Login", "Sign Up"]
choice = st.sidebar.selectbox("Menu", menu)

# -------------------- SIGNUP --------------------
if choice == "Sign Up":
    st.subheader("Create New Account")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        if not validate_email(email):
            st.error("❌ Please enter a valid, non-temporary email (e.g., Gmail, Outlook, Yahoo).")
        elif signup_user(username, email, password):
            st.success("✅ Account created successfully! You can now log in.")
        else:
            st.error("⚠️ Username already exists. Try another.")

# -------------------- LOGIN --------------------
elif choice == "Login":
    st.subheader("Login to Your Account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        user = login_user(username, password)
        if user:
            st.success(f"Welcome back, {username}! 🎉")

            city = st.text_input("Enter your city:")
            if city:
                weather_data = get_weather(city)
                if weather_data:
                    st.subheader(f"🌍 Weather in {city.capitalize()} ({datetime.now().strftime('%d %b %Y')})")

                    temp = weather_data["main"]["temp"]
                    humidity = weather_data["main"]["humidity"]
                    air_quality = 75  # Placeholder value (you can integrate a real AQI API later)

                    st.write(f"**Temperature:** {temp} °C")
                    st.write(f"**Humidity:** {humidity}%")
                    st.write(f"**Air Quality Index (approx):** {air_quality}")

                    st.subheader("🩺 Health Advice")
                    for tip in health_advice(temp, humidity, air_quality):
                        st.write(f"- {tip}")
                else:
                    st.error("City not found! Please try again.")
        else:
            st.error("Invalid username or password.")
