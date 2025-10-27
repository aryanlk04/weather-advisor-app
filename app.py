import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
import requests
import re

# -------------------- STREAMLIT CONFIG --------------------
st.set_page_config(page_title="Health Advisor", page_icon="🩺", layout="centered")
st.title("🩺 HealthCare Advisor")
st.write("Get personalized health guidance based on your city’s weather!")

# -------------------- DATABASE SETUP --------------------
conn = sqlite3.connect("users.db", check_same_thread=False)
cursor = conn.cursor()

# User table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash BLOB NOT NULL,
    signup_date TEXT,
    last_login TEXT
)
""")

# Preferences table
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

# -------------------- LOCAL EMAIL VALIDATION --------------------
def is_valid_email(email: str) -> bool:
    """Check for valid format and block disposable domains."""
    if not email:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(pattern, email):
        return False

    # Block disposable / fake domains
    blocked = ["tempmail", "10minutemail", "guerrillamail", "mailinator", "yopmail"]
    if any(b in email.lower() for b in blocked):
        return False

    return True

# -------------------- WEATHER FUNCTION --------------------
def get_weather(city):
    """Fetch weather data from OpenWeather API."""
    try:
        api_key = st.secrets["OPENWEATHER_API_KEY"]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        r = requests.get(url)
        if r.status_code == 200:
            data = r.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["description"]
            }
    except Exception as e:
        print("Error:", e)
    return None

# -------------------- HEALTH ADVICE FUNCTION --------------------
def health_advice(temp, humidity, condition):
    advice = []
    # Temperature-based
    if temp >= 35:
        advice += [
            "🥵 It's very hot! Stay hydrated and avoid outdoor activity in afternoon.",
            "Use SPF 30+ sunscreen.",
            "Wear light, breathable clothes."
        ]
    elif temp <= 10:
        advice += [
            "❄️ It's cold! Dress warmly in layers.",
            "Use moisturizer to prevent dry skin."
        ]
    else:
        advice.append("😊 Comfortable temperature! Maintain hydration and a balanced diet.")

    # Humidity-based
    if humidity > 80:
        advice.append("💧 High humidity — keep rooms ventilated and avoid damp areas.")
    elif humidity < 30:
        advice.append("🌵 Dry air — apply moisturizer and drink plenty of water.")

    # Condition-based
    if "rain" in condition.lower():
        advice.append("☔ Rainy weather — carry an umbrella and avoid getting wet.")
    if "haze" in condition.lower() or "smoke" in condition.lower():
        advice.append("😷 Air quality alert — wear a mask when outdoors.")
    if "snow" in condition.lower():
        advice.append("❄️ Snowy — wear insulated footwear to prevent slips.")

    return advice

# -------------------- DATABASE HELPERS --------------------
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

# -------------------- SESSION MANAGEMENT --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None

# -------------------- MAIN APP --------------------
if st.session_state.logged_in:
    st.success(f"Welcome, {st.session_state.email} 👋")

    # Load saved city
    saved_city = get_preference(st.session_state.user_id)
    city = st.text_input("Enter your city:", value=saved_city)

    if st.button("Get Health Advice"):
        if not city.strip():
            st.warning("Please enter a valid city name.")
        else:
            weather = get_weather(city.strip())
            if not weather:
                st.error("City not found or API error. Try again.")
            else:
                st.subheader(f"🌍 Weather in {city.capitalize()}")
                st.metric("Temperature (°C)", weather["temp"])
                st.metric("Humidity (%)", weather["humidity"])
                st.info(f"Condition: {weather['condition'].capitalize()}")

                st.subheader("🩺 Health Advice")
                for tip in health_advice(weather["temp"], weather["humidity"], weather["condition"]):
                    st.write(f"- {tip}")

                # Save latest weather
                save_preference(st.session_state.user_id, city, weather["temp"], weather["humidity"])

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.email = None
        st.experimental_rerun()

else:
    st.sidebar.header("Account Access")
    choice = st.sidebar.radio("Select Action", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    # ---------- SIGN UP ----------
    if choice == "Sign Up":
        if st.sidebar.button("Create Account"):
            if not email or not password:
                st.sidebar.error("Please enter both email and password.")
            elif not is_valid_email(email):
                st.sidebar.error("Please enter a valid, non-disposable email.")
            else:
                cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                if cursor.fetchone():
                    st.sidebar.error("Email already registered.")
                else:
                    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    cursor.execute("INSERT INTO users (email, password_hash, signup_date) VALUES (?, ?, ?)",
                                   (email, pw_hash, str(datetime.now())))
                    conn.commit()
                    st.sidebar.success("✅ Account created! Please log in.")

    # ---------- LOGIN ----------
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
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid email or password.")
