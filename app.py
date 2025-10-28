import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice

# ------------------ PAGE SETUP ------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")

# -------------------- Custom Top Navigation --------------------
st.markdown("""
    <style>
    .topnav {
        background-color: #f0f2f6;
        overflow: hidden;
        text-align: center;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 25px;
    }
    .topnav a {
        display: inline-block;
        color: #333;
        text-align: center;
        padding: 10px 22px;
        text-decoration: none;
        font-size: 18px;
        font-weight: 600;
        transition: 0.3s;
    }
    .topnav a:hover {
        background-color: #4CAF50;
        color: white;
        border-radius: 6px;
    }
    .active {
        background-color: #4CAF50;
        color: white !important;
        border-radius: 6px;
    }
    </style>
""", unsafe_allow_html=True))

# -------------------- Navigation Logic --------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"

def nav_click(page):
    st.session_state.page = page

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("🏠 Home"):
        nav_click("Home")
with col2:
    if st.button("ℹ️ About"):
        nav_click("About")
with col3:
    if st.button("📞 Contact"):
        nav_click("Contact")

st.markdown("<hr>", unsafe_allow_html=True)
# ------------------ HEADER ------------------
st.markdown("<h1 class='main-title' id='home'>🩺 HealthCare Advisor</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Personalized health insights based on your local weather conditions.</p>", unsafe_allow_html=True)
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

# -------------------- HOME PAGE --------------------
if st.session_state.page == "Home":
    st.title("🩺 Health Advisory App")
    st.subheader("Stay safe & healthy based on your local weather")

# If logged in
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
        st.info("Please log in or sign up below to get personalized health advice.")

        tab1, tab2 = st.tabs(["🔑 Login", "🆕 Sign Up"])

        with tab1:
            email = st.text_input("Email", key="login_email")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
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
                    st.error("❌ Invalid email or password!")

        with tab2:
            email = st.text_input("New Email", key="signup_email")
            password = st.text_input("New Password", type="password", key="signup_password")
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
                    st.success("✅ Account created successfully! Please log in now.")

# -------------------- ABOUT PAGE --------------------
elif st.session_state.page == "About":
    st.title("💬 About Health Advisor")
    st.markdown("""
    The **Health Advisor App** is designed to help you stay healthy and make smart daily choices  
    based on real-time weather conditions in your city.

    🌤 **What it does:**
    - Analyzes temperature, humidity, and weather type  
    - Suggests personalized **health tips** for your environment  
    - Encourages **preventive care** (e.g., hydration, skincare, air quality)  

    🩺 This app blends **technology + wellness** — making weather data meaningful for your health.
    """)

# -------------------- CONTACT PAGE --------------------
elif st.session_state.page == "Contact":
    st.title("📞 Contact Us")
    st.markdown("""
    Have a question or need help?  
    We’re here for you! 💬  

    - 📱 **Phone:** 90195 31192  
    - 📧 **Email:** support@healthadvisor.ai  
    - 🏢 **Office:** HealthTech Street, Bengaluru, India
