import streamlit as st
import sqlite3
import re
import bcrypt
import requests
from datetime import datetime

# ---------------------- PAGE CONFIG ----------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")

st.title("🩺 HealthCare Advisor")
st.write("Your personalized health assistant that gives you weather-based health advice.")

# ---------------------- DATABASE SETUP ----------------------
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL,
    signup_date TEXT,
    last_login TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    city TEXT,
    last_temp REAL,
    last_humidity REAL,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# ---------------------- EMAIL VALIDATION ----------------------
def is_valid_email(email):
    """Basic email format + Gmail domain check."""
    if not email:
        return False
    email_pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(email_pattern, email):
        return False
    # prevent disposable/fake domains
    banned_domains = ["tempmail", "mailinator", "yopmail", "guerrillamail"]
    if any(domain in email.lower() for domain in banned_domains):
        return False
    return True

# ---------------------- WEATHER FETCH ----------------------
def get_weather(city):
    """
    Uses OpenWeatherMap public data (no personal API key required).
    """
    try:
        url = f"https://wttr.in/{city}?format=j1"  # simple JSON weather API
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            area = data["nearest_area"][0]["areaName"][0]["value"]
            temp = float(data["current_condition"][0]["temp_C"])
            humidity = float(data["current_condition"][0]["humidity"])
            condition = data["current_condition"][0]["weatherDesc"][0]["value"]
            return {"city": area, "temp": temp, "humidity": humidity, "condition": condition}
    except Exception as e:
        print("Weather error:", e)
    return None

# ---------------------- HEALTH ADVICE ----------------------
def health_advice(temp, humidity, condition):
    """Provide health guidance based on weather."""
    advice = []

    # Temperature-based advice
    if temp >= 35:
        advice += [
            "🥵 Very hot! Stay hydrated and avoid outdoor activity during peak sun hours.",
            "Use sunscreen (SPF 30+) and wear light, loose clothing.",
            "Eat water-rich foods like watermelon or cucumber."
        ]
    elif temp <= 10:
        advice += [
            "❄️ Cold weather! Dress warmly in layers.",
            "Keep extremities covered and use moisturizer for dry skin.",
            "Consume warm fluids like soups and herbal teas."
        ]
    else:
        advice.append("😊 Pleasant temperature! Maintain a balanced diet and stay hydrated.")

    # Humidity-based advice
    if humidity > 80:
        advice.append("💧 High humidity can cause fatigue — stay in ventilated places and shower regularly.")
    elif humidity < 30:
        advice.append("🌵 Dry air — use moisturizer and drink plenty of water to prevent dehydration.")

    # Weather condition–specific advice
    condition_lower = condition.lower()
    if "rain" in condition_lower:
        advice.append("☔ It's raining! Carry an umbrella and wear waterproof footwear.")
    if "snow" in condition_lower:
        advice.append("❄️ Snowfall detected! Watch for icy surfaces and wear warm gloves.")
    if "haze" in condition_lower or "smoke" in condition_lower:
        advice.append("😷 Poor air quality — wear a mask and avoid outdoor exertion.")
    if "sunny" in condition_lower:
        advice.append("🕶 Bright sun — wear sunglasses and apply sunscreen before going out.")

    return advice

# ---------------------- HELPERS ----------------------
def save_preference(user_id, city, temp, humidity):
    cursor.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE preferences SET city=?, last_temp=?, last_humidity=? WHERE user_id=?",
                       (city, temp, humidity, user_id))
    else:
        cursor.execute("INSERT INTO preferences(user_id, city, last_temp, last_humidity) VALUES (?, ?, ?, ?)",
                       (user_id, city, temp, humidity))
    conn.commit()

def get_preference(user_id):
    cursor.execute("SELECT city FROM preferences WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else ""

# ---------------------- SESSION SETUP ----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None

# ---------------------- MAIN APP ----------------------
if st.session_state.logged_in:
    st.success(f"Welcome, {st.session_state.email}! 👋")

    saved_city = get_preference(st.session_state.user_id)
    city = st.text_input("Enter your city name:", value=saved_city)

    if st.button("Get Health Advisory"):
        if not city.strip():
            st.warning("Please enter a valid city.")
        else:
            w = get_weather(city.strip())
            if not w:
                st.error("City not found or weather API error.")
            else:
                st.subheader(f"🌍 Current Weather in {w['city']}")
                st.metric("Temperature (°C)", w["temp"])
                st.metric("Humidity (%)", w["humidity"])
                st.info(f"Condition: {w['condition'].capitalize()}")

                st.subheader("🩺 Health Advice for You:")
                for tip in health_advice(w["temp"], w["humidity"], w["condition"]):
                    st.write(f"- {tip}")

                save_preference(st.session_state.user_id, city, w["temp"], w["humidity"])

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.email = None
        st.rerun()

else:
    st.sidebar.header("Account Access")
    choice = st.sidebar.radio("Choose Action", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    # ---- SIGNUP ----
    if choice == "Sign Up":
        if st.sidebar.button("Create Account"):
            if not email or not password:
                st.sidebar.error("Please enter both email and password.")
            elif not is_valid_email(email):
                st.sidebar.error("Please use a valid Gmail or non-disposable email.")
            else:
                cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                if cursor.fetchone():
                    st.sidebar.error("Email already registered.")
                else:
                    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    cursor.execute("INSERT INTO users (email, password_hash, signup_date) VALUES (?, ?, ?)",
                                   (email, pw_hash, str(datetime.now())))
                    conn.commit()
                    st.sidebar.success("✅ Account created! Please log in now.")

    # ---- LOGIN ----
    elif choice == "Login":
        if st.sidebar.button("Login"):
            cursor.execute("SELECT id, password_hash FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode(), user[1]):
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.email = email
                cursor.execute("UPDATE users SET last_login=? WHERE id=?", (str(datetime.now()), user[0]))
                conn.commit()
                st.rerun()
            else:
                st.sidebar.error("Invalid credentials.")
