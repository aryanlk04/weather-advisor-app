import streamlit as st
import sqlite3
import requests
import sendgrid
from sendgrid.helpers.mail import Mail
from datetime import datetime

# -----------------------------
# Database setup
# -----------------------------
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT,
            email TEXT,
            password TEXT,
            city TEXT,
            last_temp REAL,
            last_humidity REAL
        )
    """)
    conn.commit()
    conn.close()

init_db()

# -----------------------------
# Email validation (diagnostic version)
# -----------------------------
def validate_email(email):
    try:
        api_key = st.secrets["EMAIL_VALIDATION_KEY"]
        url = f"https://emailvalidation.abstractapi.com/v1/?api_key={api_key}&email={email}"
        response = requests.get(url)
        data = response.json()

        # Diagnostic output
        st.write("🔍 API Response:", data)

        is_valid_format = data.get("is_valid_format", {}).get("value", False)
        is_disposable = data.get("is_disposable_email", {}).get("value", True)
        is_deliverable = data.get("deliverability", "") == "DELIVERABLE"

        if is_valid_format and not is_disposable and is_deliverable:
            return True
        else:
            return False
    except Exception as e:
        st.error(f"Error during email validation: {e}")
        return False

# -----------------------------
# SendGrid email sender
# -----------------------------
def send_email(to_email, subject, message):
    try:
        sg = sendgrid.SendGridAPIClient(api_key=st.secrets["SENDGRID_API_KEY"])
        email = Mail(
            from_email=(st.secrets["SENDER_EMAIL"], st.secrets["SENDER_NAME"]),
            to_emails=to_email,
            subject=subject,
            html_content=message
        )
        sg.send(email)
    except Exception as e:
        st.error(f"Email sending failed: {e}")

# -----------------------------
# Weather fetcher
# -----------------------------
def get_weather(city):
    try:
        api_key = st.secrets["OPENWEATHER_API_KEY"]
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric"
        data = requests.get(url).json()
        if data.get("cod") != 200:
            st.error("City not found. Please check the name.")
            return None
        return {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "description": data["weather"][0]["description"].capitalize()
        }
    except Exception as e:
        st.error(f"Weather data error: {e}")
        return None

# -----------------------------
# Health advice generator
# -----------------------------
def get_health_advice(temp, humidity, desc):
    advice = []
    if temp > 35:
        advice.append("🥵 Stay hydrated and avoid going out in the afternoon sun.")
        advice.append("🧴 Apply sunscreen SPF 30+ when outdoors.")
        advice.append("🧢 Wear light, breathable clothing.")
    elif temp < 10:
        advice.append("🧥 Dress warmly in layers.")
        advice.append("☕ Drink warm fluids to maintain body temperature.")
    else:
        advice.append("😊 The temperature is comfortable for most activities.")

    if humidity > 80:
        advice.append("💧 High humidity detected — use an anti-fungal powder to prevent rashes.")
        advice.append("😷 Consider using an N95 mask if you have breathing issues.")
    elif humidity < 30:
        advice.append("🌵 Low humidity — apply moisturizer to prevent dry skin.")

    if "rain" in desc.lower():
        advice.append("🌧 Carry an umbrella and waterproof footwear.")
    elif "dust" in desc.lower() or "smoke" in desc.lower():
        advice.append("😷 Air quality may be poor — use a mask outdoors.")

    return advice

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🏥 Health Advisor App")

menu = ["Login", "Sign Up"]
choice = st.sidebar.selectbox("Menu", menu)

conn = sqlite3.connect("users.db")
c = conn.cursor()

if choice == "Sign Up":
    st.subheader("Create Account")

    username = st.text_input("Username")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        if not validate_email(email):
            st.error("⚠️ Please provide a real or non-disposable email.")
        else:
            c.execute("SELECT * FROM users WHERE username=?", (username,))
            if c.fetchone():
                st.warning("Username already exists. Try a different one.")
            else:
                c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                          (username, email, password, None, None, None))
                conn.commit()
                st.success("✅ Account created successfully! Please log in.")

elif choice == "Login":
    st.subheader("Login to Your Account")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()
        if user:
            st.success(f"Welcome, {username}!")
            city = st.text_input("Enter your city:")
            if st.button("Check Weather"):
                weather = get_weather(city)
                if weather:
                    temp = weather["temp"]
                    humidity = weather["humidity"]
                    desc = weather["description"]

                    st.metric("🌡 Temperature", f"{temp} °C")
                    st.metric("💧 Humidity", f"{humidity} %")
                    st.write("🌦 Condition:", desc)

                    advice = get_health_advice(temp, humidity, desc)
                    st.subheader("🩺 Health Advice:")
                    for tip in advice:
                        st.write("-", tip)

                    # Send email alert
                    email_body = f"""
                    <h3>Health Update for {city}</h3>
                    <p><b>Temperature:</b> {temp} °C</p>
                    <p><b>Humidity:</b> {humidity} %</p>
                    <p><b>Condition:</b> {desc}</p>
                    <p><b>Health Tips:</b></p>
                    <ul>{''.join(f'<li>{tip}</li>' for tip in advice)}</ul>
                    <p>Stay safe and healthy!<br>— Health Advisor</p>
                    """
                    send_email(user[1], f"Your Health Advisory for {city}", email_body)
                    st.success("📧 Health update sent to your registered email!")

                    # Save city and last weather
                    c.execute("UPDATE users SET city=?, last_temp=?, last_humidity=? WHERE username=?",
                              (city, temp, humidity, username))
                    conn.commit()
        else:
            st.error("Invalid username or password.")

conn.close()
