import streamlit as st
import sqlite3
import re
import bcrypt
import requests
from datetime import datetime

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")
st.title("🩺 HealthCare Advisor")
st.write("Get personalized health tips based on your local weather conditions.")

# ---------------------- DATABASE ----------------------
DB_FILE = "users.db"

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
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
    return conn, cursor

conn, cursor = init_db()

# ---------------------- WEATHER API ----------------------
def get_weather(city):
    """Fetch weather data using OpenWeather API."""
    try:
        api_key = st.secrets["OPENWEATHER_API_KEY"]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            temp = float(data["main"]["temp"])
            humidity = float(data["main"]["humidity"])
            condition = data["weather"][0]["description"]
            return {"temp": temp, "humidity": humidity, "condition": condition}
    except Exception as e:
        print("Weather API error:", e)
    return None

# ---------------------- HEALTH ADVICE ----------------------
def health_advice(temp, humidity, condition):
    """Return list of health tips based on weather."""
    tips = []

    if temp >= 35:
        tips += [
            "🥵 Extreme heat — stay hydrated and avoid prolonged sun exposure.",
            "Use SPF 30+ sunscreen and wear light-colored, breathable clothes.",
            "Avoid outdoor exercise in the afternoon."
        ]
    elif temp <= 10:
        tips += [
            "❄️ Cold weather — wear warm clothes and drink hot fluids.",
            "Avoid sudden temperature changes to prevent colds or flu."
        ]
    else:
        tips.append("😊 Pleasant temperature — maintain regular hydration and a balanced diet.")

    if humidity > 80:
        tips.append("💧 High humidity — stay in well-ventilated areas and prevent dehydration.")
    elif humidity < 30:
        tips.append("🌵 Dry air — use moisturizer and drink plenty of water.")

    c = condition.lower()
    if "rain" in c:
        tips.append("☔ Rainy conditions — carry an umbrella and avoid getting wet.")
    if "haze" in c or "smoke" in c:
        tips.append("😷 Poor air quality — use an N95 mask when outdoors.")
    if "sun" in c or "clear" in c:
        tips.append("🕶 Sunny weather — wear sunglasses and apply sunscreen.")
    if "snow" in c:
        tips.append("❄️ Snowfall — wear insulated shoes and warm gloves.")

    return tips

# ---------------------- PREFERENCES ----------------------
def get_preference(user_id):
    cursor.execute("SELECT city, last_temp, last_humidity FROM preferences WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if r:
        return {"city": r[0], "last_temp": r[1], "last_humidity": r[2]}
    return None

def save_preference(user_id, city, temp, humidity):
    cursor.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE preferences SET city=?, last_temp=?, last_humidity=? WHERE user_id=?",
                       (city, temp, humidity, user_id))
    else:
        cursor.execute("INSERT INTO preferences (user_id, city, last_temp, last_humidity) VALUES (?, ?, ?, ?)",
                       (user_id, city, temp, humidity))
    conn.commit()

# ---------------------- SESSION ----------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None

# ---------------------- MAIN APP ----------------------
if st.session_state.logged_in:
    st.success(f"Welcome, {st.session_state.email}! 👋")

    pref = get_preference(st.session_state.user_id)
    saved_city = pref["city"] if pref else ""
    city = st.text_input("Enter your city:", value=saved_city)

    if st.button("Check Health Advisory"):
        if not city.strip():
            st.warning("Please enter a city name.")
        else:
            w = get_weather(city.strip())
            if not w:
                st.error("City not found or API issue.")
            else:
                st.subheader(f"🌍 Weather in {city.capitalize()}")
                st.metric("Temperature (°C)", w["temp"])
                st.metric("Humidity (%)", w["humidity"])
                st.info(f"Condition: {w['condition'].capitalize()}")

                st.subheader("🩺 Health Tips")
                for t in health_advice(w["temp"], w["humidity"], w["condition"]):
                    st.write(f"- {t}")

                save_preference(st.session_state.user_id, city, w["temp"], w["humidity"])

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.email = None
        st.rerun()

else:
    st.sidebar.header("Account Access")
    action = st.sidebar.radio("Select:", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    conn, cursor = init_db()

    if action == "Sign Up":
        if st.sidebar.button("Create Account"):
            if not email or not password:
                st.sidebar.error("Please enter both email and password.")
            else:
                cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                if cursor.fetchone():
                    st.sidebar.error("Email already registered.")
                else:
                    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    cursor.execute("INSERT INTO users (email, password_hash, signup_date) VALUES (?, ?, ?)",
                                   (email, hashed, str(datetime.now())))
                    conn.commit()
                    st.sidebar.success("✅ Account created! Please log in.")

    elif action == "Login":
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



