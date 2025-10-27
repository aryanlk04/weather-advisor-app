import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
import requests
import re

# -------------------- STREAMLIT CONFIG --------------------
st.set_page_config(page_title="Health Advisor", page_icon="🩺", layout="centered")
st.title("🩺 HealthCare Advisor")
st.write("Personalized health guidance based on your local weather. Sign up with a valid email to get health alerts.")

# -------------------- DATABASE SETUP --------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
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
    last_notified TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# -------------------- SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None

# -------------------- CONFIG --------------------
TEMP_THRESHOLD = 2.0      # degrees Celsius
HUMIDITY_THRESHOLD = 10   # percent

# -------------------- LOCAL EMAIL VALIDATION --------------------
def is_real_email(email: str) -> bool:
    """Check email syntax and block disposable domains."""
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    if not re.match(pattern, email):
        return False

    disposable_domains = [
        "tempmail", "10minutemail", "guerrillamail",
        "yopmail", "mailinator", "trashmail"
    ]
    if any(d in email.lower() for d in disposable_domains):
        return False

    valid_providers = ["gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com"]
    if not any(email.lower().endswith(provider) for provider in valid_providers):
        return False

    return True

# -------------------- WEATHER FUNCTIONS --------------------
def get_weather(city):
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
    return None

# -------------------- HEALTH ADVICE --------------------
def health_advice(temp, humidity, condition):
    advice = []
    if temp > 35:
        advice += [
            "☀️ Extremely hot! Stay hydrated and avoid direct sunlight.",
            "Use SPF 30+ sunscreen before stepping out.",
            "Wear light, breathable clothing."
        ]
    elif temp < 10:
        advice += [
            "❄️ Cold weather! Dress warmly and keep your skin moisturized.",
            "Drink warm fluids to stay hydrated."
        ]
    else:
        advice.append("🌤️ Comfortable weather — maintain hydration and a balanced diet.")

    if humidity > 80:
        advice.append("💧 High humidity — use antifungal powder and keep rooms ventilated.")
    elif humidity < 30:
        advice.append("🌵 Dry air — use moisturizer and stay hydrated.")

    if "smoke" in condition.lower() or "haze" in condition.lower():
        advice.append("😷 Poor air quality — consider wearing an N95 mask.")

    return advice

# -------------------- DATABASE HELPERS --------------------
def save_user_pref(user_id, city, temp=None, humidity=None):
    cursor.execute("SELECT * FROM preferences WHERE user_id=?", (user_id,))
    if cursor.fetchone():
        cursor.execute("UPDATE preferences SET city=?, last_temp=?, last_humidity=? WHERE user_id=?",
                       (city, temp, humidity, user_id))
    else:
        cursor.execute("INSERT INTO preferences(user_id, city, last_temp, last_humidity) VALUES (?, ?, ?, ?)",
                       (user_id, city, temp, humidity))
    conn.commit()

def get_user_pref(user_id):
    cursor.execute("SELECT city, last_temp, last_humidity FROM preferences WHERE user_id=?", (user_id,))
    r = cursor.fetchone()
    if r:
        return {"city": r[0], "last_temp": r[1], "last_humidity": r[2]}
    return None

# -------------------- MAIN APP --------------------
if st.session_state.logged_in:
    st.success(f"Welcome back, {st.session_state.email}!")

    pref = get_user_pref(st.session_state.user_id)
    if pref and pref.get("city"):
        st.info(f"Your saved city: **{pref['city']}** (Temp: {pref['last_temp']}°C, Humidity: {pref['last_humidity']}%)")

    city = st.text_input("Enter your city:")
    if st.button("Check Weather & Health Advice"):
        if not city.strip():
            st.warning("Please enter a city name.")
        else:
            w = get_weather(city)
            if not w:
                st.error("City not found or API error.")
            else:
                st.subheader(f"🌍 Weather in {city.capitalize()} — {datetime.now().strftime('%d %b %Y')}")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Temperature (°C)", w["temp"])
                    st.metric("Humidity (%)", w["humidity"])
                with col2:
                    st.info(f"Condition: {w['condition'].capitalize()}")

                st.subheader("🩺 Health Advice")
                for tip in health_advice(w["temp"], w["humidity"], w["condition"]):
                    st.write(f"- {tip}")

                save_user_pref(st.session_state.user_id, city, w["temp"], w["humidity"])

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.user_id = None
        st.session_state.email = None
        st.experimental_rerun()

else:
    st.sidebar.header("Account")
    choice = st.sidebar.selectbox("Action", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.sidebar.button("Sign Up"):
            if not email or not password:
                st.sidebar.error("Please enter both email and password.")
            elif not is_real_email(email):
                st.sidebar.error("Invalid or disposable email. Please use Gmail, Outlook, etc.")
            else:
                cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                if cursor.fetchone():
                    st.sidebar.error("Email already registered.")
                else:
                    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                    cursor.execute("INSERT INTO users(email, password_hash, signup_date) VALUES (?, ?, ?)",
                                   (email, pw_hash, str(datetime.now())))
                    conn.commit()
                    st.sidebar.success("✅ Account created! Please log in.")

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
                st.sidebar.error("Invalid credentials.")
