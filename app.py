import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Health Advisor 🌤", page_icon="🩺", layout="centered")

# -------------------- MOBILE-FRIENDLY CUSTOM CSS --------------------
st.markdown("""
    <style>
    body {
        background-color: #f7f9fc;
        font-family: 'Segoe UI', sans-serif;
    }

    /* Center everything on small screens */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
        .nav-button {
            width: 90% !important;
            margin: 5px auto !important;
            display: block !important;
        }
    }

    .nav-container {
        text-align: center;
        margin-bottom: 20px;
    }

    .nav-button {
        background: linear-gradient(90deg, #4ba3e3, #5ec576);
        color: white;
        border: none;
        padding: 10px 20px;
        font-size: 17px;
        font-weight: 600;
        border-radius: 8px;
        margin: 5px 10px;
        cursor: pointer;
        transition: all 0.3s ease;
    }

    .nav-button:hover {
        transform: scale(1.05);
        opacity: 0.9;
    }

    .active {
        background: linear-gradient(90deg, #2196F3, #4CAF50);
        box-shadow: 0 0 12px rgba(72, 239, 128, 0.8);
        transform: scale(1.05);
    }

    .metric-container {
        text-align: center;
        margin-top: 10px;
    }

    .footer {
        text-align: center;
        color: gray;
        font-size: 14px;
        margin-top: 50px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- NAVIGATION --------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"

st.markdown('<div class="nav-container">', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 Home", key="home_btn"):
        st.session_state.page = "Home"
with col2:
    if st.button("ℹ️ About", key="about_btn"):
        st.session_state.page = "About"
with col3:
    if st.button("📞 Contact", key="contact_btn"):
        st.session_state.page = "Contact"

st.markdown('</div>', unsafe_allow_html=True)

# -------------------- DATABASE --------------------
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

                    # Save preference
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
            st.rerun()

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
                    st.rerun()
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

# -------------------- FOOTER --------------------
st.markdown("<p class='footer'>© 2025 Health Advisor | Stay Weather-Smart 🌦</p>", unsafe_allow_html=True)

