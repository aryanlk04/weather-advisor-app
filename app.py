import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice

# -------------------- Page Config --------------------
st.set_page_config(
    page_title="Health Advisor 🌤",
    page_icon="🩺",
    layout="centered"
)

# -------------------- Custom CSS for Beautiful Top Navigation --------------------
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

# -------------------- Navigation Buttons --------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"

def nav_click(page):
    st.session_state.page = page

st.markdown("""
<div class="topnav">
    <a href="#" onclick="window.parent.postMessage('Home','*')">🏠 Home</a>
    <a href="#" onclick="window.parent.postMessage('About','*')">ℹ️ About</a>
    <a href="#" onclick="window.parent.postMessage('Contact','*')">📞 Contact</a>
</div>
""", unsafe_allow_html=True)

# Simulate JS navigation event listener
nav_event = st.session_state.page

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
    The **Health Advisor App** combines live weather data with medical insight to help you make better daily health choices.

    🌤 **What It Does:**
    - Analyzes local weather (temperature, humidity, condition)  
    - Suggests **custom health care tips** to protect your skin, hydration, and immunity  
    - Helps you stay **proactive** about your wellness  

    💚 Whether it’s hot, humid, or dry — we give you the right health advice at the right time.
    """)

# -------------------- CONTACT PAGE --------------------
elif st.session_state.page == "Contact":
    st.title("📞 Contact Us")
    st.markdown("""
    Have a question or feedback?  
    We're happy to help you! 💬  

    - 📱 **Phone:** 90195 31192  
    - 📧 **Email:** support@healthadvisor.ai  
    - 🏢 **Office:** HealthTech Street, Bengaluru, India  
    """)
