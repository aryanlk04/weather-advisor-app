import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice

# ------------------ PAGE SETUP ------------------
st.set_page_config(page_title="HealthCare Advisor", page_icon="🩺", layout="centered")

# ------------------ CUSTOM STYLE ------------------
st.markdown("""
    <style>
    /* Global background with subtle healthcare theme */
    [data-testid="stAppViewContainer"] {
        background-image: url('https://images.unsplash.com/photo-1588776814546-46e61ab46d81?auto=format&fit=crop&w=1500&q=80');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    [data-testid="stHeader"] {
        background: rgba(255,255,255,0);
    }

    /* Navigation bar */
    .nav {
        background-color: rgba(255, 255, 255, 0.8);
        padding: 0.7em 1.5em;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 20px;
    }
    .nav a {
        text-decoration: none;
        color: #0077b6;
        font-weight: 600;
        margin: 0 15px;
        font-size: 1.1em;
    }
    .nav a:hover {
        color: #0096c7;
        text-decoration: underline;
    }

    /* Main title */
    .main-title {
        text-align: center;
        color: #023e8a;
        font-size: 2.6rem;
        font-weight: 700;
        margin-top: -10px;
    }
    .subtitle {
        text-align: center;
        color: #03045e;
        font-size: 1rem;
        margin-bottom: 25px;
    }

    /* Cards */
    .card {
        background: rgba(255, 255, 255, 0.9);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        margin-bottom: 20px;
    }

    /* Buttons */
    div.stButton > button {
        background-color: #0077b6;
        color: white;
        font-weight: 600;
        border-radius: 8px;
        padding: 0.6em 1.3em;
        transition: 0.3s;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #0096c7;
        transform: scale(1.03);
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: rgba(173, 232, 244, 0.9);
    }

    /* Footer */
    .footer {
        text-align: center;
        color: #555;
        font-size: 0.9em;
        margin-top: 30px;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------- Navigation --------------------
st.sidebar.title("🌐 Navigation")
page = st.sidebar.radio("Go to", ["Home", "About", "Contact"])
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
if page == "Home":
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
                # -------------------- ABOUT PAGE --------------------
if page == "About":
    st.title("💬 About Health Advisor")
    st.write("""
    **Health Advisor** helps users make informed health decisions based on their local weather conditions.  
    It provides personalized advice on:
    - 🌞 Sun safety and hydration during heatwaves  
    - ❄️ Protection against cold and dry weather  
    - 💧 Humidity-based skin and respiratory tips  
    - 😷 Air quality and pollution precautions  

    This web app integrates live weather data and turns it into simple, practical health guidance so you can stay healthy every day.  
    """)

# -------------------- CONTACT PAGE --------------------
if page == "Contact":
    st.title("📞 Contact Us")
    st.write("""
    For support or inquiries, feel free to reach out:

    - 📱 **Phone:** 90195 31192  
    - 📧 **Email:** support@healthadvisor.ai  
    - 🏢 **Address:** HealthTech Street, Bengaluru, India  

    We’re always happy to help you stay healthy and informed! 💙
    """)






