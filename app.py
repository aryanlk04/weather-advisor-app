import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
import requests
import re
import os

# -------------------- STREAMLIT CONFIG --------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")
st.title("🩺 HealthCare Advisor")
st.write("Get personalized health guidance based on your city’s weather!")

# -------------------- DATABASE SETUP --------------------
DB_PATH = "database.db"

# Ensure DB and tables exist before anything else
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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

# -------------------- EMAIL VALIDATION --------------------
def is_valid_email(email: str) -> bool:
    """Check if email looks valid and not disposable."""
    if not email:
        return False
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(pattern, email):
        return False

    blocked_domains = ["tempmail", "10minutemail", "guerrillamail", "mailinator", "yopmail"]
    if any(b in email.lower() for b in blocked_domains):
        return False

    return True

# -------------------- WEATHER FUNCTION --------------------
def get_weather(city):
    """Fetch weather data from OpenWeather API."""
    try:
        api_key = st.secrets["OPENWEATHER_API_KEY"]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            return {
                "temp": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "condition": data["weather"][0]["description"]
            }
    except Exception as e:
        print("Weather API Error:", e)
    return None

# -------------------- HEALTH ADVICE --------------------
def health_advice(temp, humidity, condition):
    advice = []
    if temp >= 35:
        advice += [
            "🥵 It's extremely hot! Stay hydrated and avoid outdoor activity during midday.",
            "Use SPF 30+ sunscreen to protect your skin.",
            "Wear light, breathable clothing."
        ]
    elif temp <= 10:
        advice += [
            "❄️ It's cold! Dress warmly and keep your hands and feet covered.",
            "Use moisturizer to prevent dry skin."
        ]
    else:
        advice.append("😊 Pleasant temperature! Stay hydrated and maintain a balanced diet.")

    if humidity > 80:
        advice.append("💧 High humidity — keep your environment well-ventilated and avoid dampness.")
    elif humidity < 30:
        advice.append("🌵 Dry air — use moisturizer and drink plenty of water.")

    if "rain" in condition.lower():
        advice.append("☔ It's raining — carry an umbrella and avoid getting drenched.")
    if "haze" in condition.lower() or "smoke" in condition.lower():
        advice.append("😷 Poor air quality — wear a mask when going outdoors.")
    if "snow" in condition.lower():
        advice.append("❄️ Snowy conditions — wear insulated footwear and stay warm.")

    return advice

# -------------------- DATABASE HELPERS --------------------
def safe_query(query, params=()):
    """Executes queries safely after ensuring tables exist."""
    try:
        cursor.execute(query, params)
        conn.commit()
    except sqlite3.OperationalError as e:
        st.warning("Reinitializing database (tables missing)...")
        init_db()
        cursor.execute(query, params)
        conn.commit()

def get_preference(user_id):
    safe_query("CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, city TEXT, last_temp REAL, last_humidity REAL, FOREIGN KEY(user_id) REFERENCES users(id))")
    cursor.execute("SELECT city FROM preferences WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    return r[0] if r else ""

def save_preference(user_id, city, temp, humidity):
    cursor.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        safe_query("UPDATE preferences SET city=?, last_temp=?, last_humidity=? WHERE user_id=?", (city, temp, humidity, user_id))
    else:
        safe_query("INSERT INTO preferences(user_id, city, last_temp, last_humidity) VALUES (?, ?, ?, ?)", (user_id, city, temp, humidity))

# -------------------- SESSION MANAGEMENT --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None

# -------------------- MAIN APP --------------------
if st.session_state.logged_in:
    st.success(f"Welcome, {st.session_state.email}! 👋")

    saved_city = get_preference(st.session_state.user_id)
    city = st.text_input("Enter your city:", value=saved_city)

    if st.button("Get Health Advice"):
        if not city.strip():
            st.warning("Please enter a valid city name.")
        else:
            weather = get_weather(city.strip())
            if not weather:
                st.error("City not found or API issue. Please try again.")
            else:
                st.subheader(f"🌍 Weather in {city.capitalize()}")
                st.metric("Temperature (°C)", weather["temp"])
                st.metric("Humidity (%)", weather["humidity"])
                st.info(f"Condition: {weather['condition'].capitalize()}")

                st.subheader("🩺 Health Advice")
                for tip in health_advice(weather["temp"], weather["humidity"], weather["condition"]):
                    st.write(f"- {tip}")

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
                try:
                    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                except sqlite3.OperationalError:
                    init_db()
                    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                if cursor.fetchone():
                    st.sidebar.error("Email already registered.")
                else:
                    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    safe_query("INSERT INTO users (email, password_hash, signup_date) VALUES (?, ?, ?)", (email, pw_hash, str(datetime.now())))
                    st.sidebar.success("✅ Account created! Please log in.")

    # ---------- LOGIN ----------
    elif choice == "Login":
        if st.sidebar.button("Login"):
            try:
                cursor.execute("SELECT id, password_hash FROM users WHERE email=?", (email,))
            except sqlite3.OperationalError:
                init_db()
                cursor.execute("SELECT id, password_hash FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode(), user[1]):
                st.session_state.logged_in = True
                st.session_state.user_id = user[0]
                st.session_state.email = email
                safe_query("UPDATE users SET last_login=? WHERE id=?", (str(datetime.now()), user[0]))
                st.experimental_rerun()
            else:
                st.sidebar.error("Invalid email or password.")
