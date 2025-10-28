import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Health Advisor 🌤", page_icon="🩺", layout="centered")

# -------------------- CUSTOM CSS --------------------
st.markdown("""
    <style>
    /* Overall background and font styling */
    body {
        background-color: #f7f9fb;
        font-family: 'Segoe UI', sans-serif;
    }

    /* Navigation bar styling */
    .topnav {
        background: linear-gradient(90deg, #5ec576, #4ba3e3);
        overflow: hidden;
        text-align: center;
        padding: 15px 10px;
        border-radius: 10px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
        margin-bottom: 30px;
    }

    .topnav a {
        display: inline-block;
        color: white;
        text-align: center;
        padding: 10px 25px;
        text-decoration: none;
        font-size: 19px;
        font-weight: 600;
        transition: all 0.3s ease;
        border-radius: 5px;
    }

    .topnav a:hover {
        background-color: rgba(255, 255, 255, 0.2);
        color: #fff;
        transform: scale(1.05);
    }

    .active {
        background-color: rgba(255, 255, 255, 0.3);
        color: #fff !important;
        font-weight: bold;
        border-radius: 6px;
    }

    /* Horizontal line styling */
    hr {
        border: 1px solid #e0e0e0;
        margin-bottom: 20px;
    }

    /* Center align buttons */
    .center {
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- NAVIGATION --------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"

# Create three columns for navigation buttons
col1, col2, col3 = st.columns([1, 1, 1])

with col1:
    if st.button("🏠 Home", use_container_width=True):
        st.session_state.page = "Home"
with col2:
    if st.button("ℹ️ About", use_container_width=True):
        st.session_state.page = "About"
with col3:
    if st.button("📞 Contact", use_container_width=True):
        st.session_state.page = "Contact"

# Add visual highlight below the active button
if st.session_state.page == "Home":
    st.markdown("<h5 style='text-align:center;color:#4ba3e3;'>🏠 You are on the Home Page</h5>", unsafe_allow_html=True)
elif st.session_state.page == "About":
    st.markdown("<h5 style='text-align:center;color:#5ec576;'>ℹ️ You are on the About Page</h5>", unsafe_allow_html=True)
else:
    st.markdown("<h5 style='text-align:center;color:#2196F3;'>📞 You are on the Contact Page</h5>", unsafe_allow_html=True)

st.write("---")

# -------------------- DATABASE SETUP --------------------
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

# -------------------- SESSION STATE --------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None

# -------------------- HOME PAGE --------------------
if st.session_state.page == "Home":
    st.title("🩺 Health Advisory App")
    st.subheader("Stay Safe & Healthy Based on Your Local Weather 🌤")

    if st.session_state.logged_in:
        st.success(f"Welcome back, {st.session_state.email}!")

        city = st.text_input("🏙️ Enter your city:")
        if st.button("Check Health Advice"):
            if city.strip() == "":
                st.warning("⚠️ Please enter a city name.")
            else:
                weather = get_weather(city.strip())
                if weather:
                    advice = health_advice(weather['temp'], weather['humidity'], weather['condition'])
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
                    cursor.execute("SELECT * FROM preferences WHERE user_id=?", (st.session_state.user_id,))
                    if cursor.fetchone():
                        cursor.execute("UPDATE preferences SET city=? WHERE user_id=?", (city.strip(), st.session_state.user_id))
                    else:
                        cursor.execute("INSERT INTO preferences(user_id, city) VALUES (?, ?)", (st.session_state.user_id, city.strip()))
                    conn.commit()
                else:
                    st.error("❌ City not found or API error. Check spelling or API key.")

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.email = None
            st.experimental_rerun()

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
    ### 🌤 Your Personal Weather-Based Health Companion  
    The **Health Advisor App** helps you stay safe and healthy by analyzing live weather data and providing tailored health advice.

    **Our Mission:**  
    Empower individuals to make better daily health choices by understanding how weather impacts their wellbeing.

    **Features:**
    - 💧 Personalized hydration and skincare reminders  
    - 🌞 Sun and pollution safety tips  
    - 🌡 Temperature-based lifestyle suggestions  

    Stay weather-smart, stay healthy! 💚
    """)

# -------------------- CONTACT PAGE --------------------
elif st.session_state.page == "Contact":
    st.title("📞 Contact Us")
    st.markdown("""
    We'd love to hear from you! 💬  

    **Phone:** 90195 31192  
    **Email:** support@healthadvisor.ai  
    **Address:** HealthTech Street, Bengaluru, India  
    """)

