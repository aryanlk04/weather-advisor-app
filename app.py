import streamlit as st
import sqlite3
import re
import bcrypt
import requests
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

# ---------------------- CONFIG ----------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")
st.title("🩺 HealthCare Advisor")
st.write("Get health tips and alerts based on your local weather conditions.")

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
        last_notified TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )
    """)
    conn.commit()
    return conn, cursor

conn, cursor = init_db()

# ---------------------- EMAIL VALIDATION ----------------------
def is_valid_email(email):
    """Simple local validation."""
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    banned_domains = ["tempmail", "mailinator", "yopmail", "guerrillamail"]
    if not re.match(pattern, email):
        return False
    if any(b in email.lower() for b in banned_domains):
        return False
    return True

# ---------------------- WEATHER API ----------------------
def get_weather(city):
    """Fetch weather data using OpenWeather API (with secret key)."""
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
        print("Weather error:", e)
    return None

# ---------------------- HEALTH ADVICE ----------------------
def health_advice(temp, humidity, condition):
    tips = []
    if temp >= 35:
        tips += [
            "🥵 Extreme heat! Stay hydrated and avoid direct sunlight.",
            "Use SPF 30+ sunscreen and wear loose, light clothes.",
            "Avoid outdoor workouts during the afternoon."
        ]
    elif temp <= 10:
        tips += [
            "❄️ Cold weather! Dress warmly and wear gloves.",
            "Drink warm fluids and avoid sudden temperature changes."
        ]
    else:
        tips.append("😊 Comfortable temperature! Perfect for light exercise and balanced diet.")

    if humidity > 80:
        tips.append("💧 High humidity — stay in well-ventilated areas to prevent fatigue.")
    elif humidity < 30:
        tips.append("🌵 Dry air — apply moisturizer and drink more water.")

    c = condition.lower()
    if "rain" in c:
        tips.append("☔ Rain expected — carry an umbrella and avoid getting drenched.")
    if "haze" in c or "smoke" in c:
        tips.append("😷 Air quality may be poor — use an N95 mask outdoors.")
    if "sun" in c or "clear" in c:
        tips.append("🕶 Sunny skies — wear sunglasses and stay hydrated.")
    if "snow" in c:
        tips.append("❄️ Snowfall — wear insulated shoes and gloves.")

    return tips

# ---------------------- NOTIFICATION EMAIL ----------------------
def send_health_email(to_email, subject, body):
    """Send email using notifier API key (SMTP or SendGrid)."""
    try:
        smtp_user = st.secrets["NOTIFIER_EMAIL"]
        smtp_pass = st.secrets["NOTIFIER_KEY"]
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_user
        msg["To"] = to_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, [to_email], msg.as_string())
        return True
    except Exception as e:
        print("Notification email failed:", e)
        return False

# ---------------------- DATABASE HELPERS ----------------------
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

def maybe_notify_on_change(user_id, email, city, old_temp, old_hum, new_temp, new_hum):
    """Send email if temp or humidity changes significantly."""
    TEMP_CHANGE = 2.5
    HUM_CHANGE = 10
    should_notify = False
    changes = []

    if old_temp is not None and abs(new_temp - old_temp) > TEMP_CHANGE:
        changes.append(f"Temperature: {old_temp}°C → {new_temp}°C")
        should_notify = True
    if old_hum is not None and abs(new_hum - old_hum) > HUM_CHANGE:
        changes.append(f"Humidity: {old_hum}% → {new_hum}%")
        should_notify = True

    if should_notify:
        advice = "\n".join(health_advice(new_temp, new_hum, ""))
        body = f"Hi,\n\nWeather in {city} has changed:\n" + "\n".join(changes) + f"\n\nHealth advice:\n{advice}"
        send_health_email(email, f"Health Alert for {city}", body)
        cursor.execute("UPDATE preferences SET last_notified=? WHERE user_id=?", (str(datetime.now()), user_id))
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

                if pref:
                    maybe_notify_on_change(st.session_state.user_id, st.session_state.email, city,
                                           pref["last_temp"], pref["last_humidity"], w["temp"], w["humidity"])
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

    if action == "Sign Up":
        if st.sidebar.button("Create Account"):
            if not email or not password:
                st.sidebar.error("Please enter both email and password.")
            elif not is_valid_email(email):
                st.sidebar.error("Invalid email address.")
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
