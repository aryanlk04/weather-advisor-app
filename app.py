import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice

# ------------------ PAGE SETUP ------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")

# Custom CSS for a modern health-themed design
st.markdown("""
    <style>
    /* Background gradient */
    body {
        background: linear-gradient(135deg, #e6f0ff 0%, #ffffff 100%);
        font-family: 'Poppins', sans-serif;
    }
    /* Main title */
    .main-title {
        text-align: center;
        color: #0077b6;
        font-size: 2.5rem;
        font-weight: 700;
        margin-top: -10px;
    }
    /* Sub text */
    .subtitle {
        text-align: center;
        color: #555;
        font-size: 1rem;
        margin-bottom: 20px;
    }
    /* Card design for weather and health info */
    .card {
        background-color: #f0f8ff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    /* Buttons */
    div.stButton > button {
        background-color: #0077b6;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.6em 1.2em;
        transition: 0.3s;
    }
    div.stButton > button:hover {
        background-color: #0096c7;
        transform: scale(1.03);
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #caf0f8;
    }
    </style>
""", unsafe_allow_html=True)

# ------------------ HEADER ------------------
st.markdown("<h1 class='main-title'>🩺 HealthCare Advisor</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Your personal health companion powered by live weather insights.</p>", unsafe_allow_html=True)
# -------------------- Database Setup --------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    signup_date TEXT,
    last_login TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    city TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# -------------------- Session State --------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['email'] = None

# ------------------ HEALTH ADVICE ------------------
def health_advice(temp, humidity, condition):
    tips = []
    if temp > 32:
        tips.append("☀️ Stay hydrated and avoid prolonged outdoor activities.")
    elif temp < 10:
        tips.append("🧣 Dress warmly to prevent catching a cold.")
    else:
        tips.append("😊 Ideal weather for outdoor walks and exercise.")

    if humidity > 80:
        tips.append("💧 High humidity — keep skin dry to prevent rashes.")
    elif humidity < 30:
        tips.append("🌵 Dry air — use moisturizer and stay hydrated.")

    if "rain" in condition.lower():
        tips.append("☔ Carry an umbrella and wear waterproof shoes.")
    elif "clear" in condition.lower():
        tips.append("😎 Use sunscreen while outdoors.")
    elif "snow" in condition.lower():
        tips.append("❄️ Keep extremities warm and avoid slippery surfaces.")

    return tips

# -------------------- Logged-in User --------------------
if st.session_state['logged_in']:
    st.success(f"Welcome back, {st.session_state['email']}!")

    weather_placeholder = st.empty()
    city = st.text_input("🏙 Enter your city")

    if st.button("Check Health Advice"):
        if city.strip() == "":
            weather_placeholder.warning("⚠️ Please enter a city name.")
        else:
            weather = get_weather(city.strip())
            if weather:
                advice = health_advice(weather['temp'], weather['humidity'], weather['condition'])

                with weather_placeholder.container():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(label="🌡 Temperature (°C)", value=weather['temp'])
                        st.metric(label="💧 Humidity (%)", value=weather['humidity'])
                    with col2:
                        st.info(f"☁️ Condition: {weather['condition'].capitalize()}")

                    st.subheader("💡 Health Recommendations:")
                    for tip in advice:
                        st.success(tip)

                    # Save or update user preference
                    cursor.execute("SELECT * FROM preferences WHERE user_id=?", (st.session_state['user_id'],))
                    if cursor.fetchone():
                        cursor.execute("UPDATE preferences SET city=? WHERE user_id=?", (city.strip(), st.session_state['user_id']))
                    else:
                        cursor.execute("INSERT INTO preferences(user_id, city) VALUES (?, ?)", (st.session_state['user_id'], city.strip()))
                    conn.commit()
            else:
                weather_placeholder.error("❌ City not found or API error. Check spelling or API key.")

    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['email'] = None
        st.rerun()

# -------------------- Login / Sign Up --------------------
else:
    choice = st.sidebar.selectbox("Login / Sign Up", ["Login", "Sign Up"])

    if choice == "Sign Up":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Sign Up"):
            cursor.execute("SELECT * FROM users WHERE email=?", (email,))
            if cursor.fetchone():
                st.error("❌ Email already registered! Try logging in.")
            else:
                password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                cursor.execute(
                    "INSERT INTO users(email, password_hash, signup_date) VALUES (?, ?, ?)",
                    (email, password_hash, str(datetime.now()))
                )
                conn.commit()
                st.success("✅ Account created! Please log in from the sidebar.")

    elif choice == "Login":
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            cursor.execute("SELECT id, password_hash FROM users WHERE email=?", (email,))
            user = cursor.fetchone()
            if user and bcrypt.checkpw(password.encode(), user[1]):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user[0]
                st.session_state['email'] = email
                cursor.execute("UPDATE users SET last_login=? WHERE id=?", (str(datetime.now()), user[0]))
                conn.commit()
                st.rerun()
            else:
                st.error("❌ Invalid email or password!")

