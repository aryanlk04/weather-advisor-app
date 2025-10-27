import streamlit as st
import sqlite3
from datetime import datetime
import bcrypt
from weather_utils import get_weather, health_advice
from email_validation import is_real_email
from notifier import send_health_email

# ---------------- Page config ----------------
st.set_page_config(page_title="Health Advisor", page_icon="🩺", layout="centered")
st.title("🩺 HealthCare Advisor")
st.write("Personalized health guidance based on local weather. Sign up with a real email to receive alerts.")

# ---------------- DB setup ----------------
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

# ---------------- session state ----------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['email'] = None

# thresholds for notifying changes
TEMP_THRESHOLD = 2.0      # degrees Celsius
HUMIDITY_THRESHOLD = 10   # percent

# --------------- helper functions ---------------
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

def maybe_notify_on_change(user_id, email, city, old_temp, old_hum, new_temp, new_hum):
    """
    If difference exceeds threshold, send email notification and update last_notified timestamp.
    Returns a message string describing what happened (or None).
    """
    parts = []
    send_email = False

    if old_temp is not None and abs(new_temp - old_temp) >= TEMP_THRESHOLD:
        parts.append(f"Temperature changed {old_temp}°C → {new_temp}°C.")
        send_email = True
    if old_hum is not None and abs(new_hum - old_hum) >= HUMIDITY_THRESHOLD:
        parts.append(f"Humidity changed {old_hum}% → {new_hum}%.")
        send_email = True

    if send_email:
        # Build email contents
        subject = f"Health Alert for {city}"
        advice_list = health_advice(new_temp, new_hum, "")
        advice_text = "\n".join(f"- {a}" for a in advice_list)
        body = f"Hello,\n\nWe detected a weather change in {city}:\n" + "\n".join(parts) + \
               f"\n\nHealth recommendations:\n{advice_text}\n\nStay safe,\nHealth Advisor"
        sent = send_health_email(email, subject, body)
        # Update last_notified timestamp
        cursor.execute("UPDATE preferences SET last_notified=? WHERE user_id=?", (str(datetime.now()), user_id))
        conn.commit()
        return f"Notification sent: {'Yes' if sent else 'Failed to send'} — reason: {'; '.join(parts)}"
    return None

# ----------------- main UI -----------------
if st.session_state['logged_in']:
    st.success(f"Welcome back, {st.session_state['email']}!")
    # show stored preference if exists
    pref = get_user_pref(st.session_state['user_id'])
    if pref and pref.get("city"):
        st.info(f"Your saved city: **{pref['city']}** (last checked temp: {pref['last_temp']}, humidity: {pref['last_humidity']})")

    city = st.text_input("Enter your city (e.g., London):", value=pref['city'] if pref else "")
    if st.button("Get Health Advice"):
        if not city.strip():
            st.warning("Please enter a city.")
        else:
            w = get_weather(city.strip())
            if not w:
                st.error("City not found or API error.")
            else:
                # display summary and health advice
                cols = st.columns(2)
                with cols[0]:
                    st.metric("🌡 Temperature (°C)", w["temp"])
                    st.metric("💧 Humidity (%)", w["humidity"])
                with cols[1]:
                    st.info(f"☁️ Condition: {w['condition'].capitalize()}")
                advice = health_advice(w["temp"], w["humidity"], w["condition"])
                st.subheader("Health Recommendations")
                for a in advice:
                    st.success(a)

                # Check for change since last saved and maybe notify
                old_temp = pref.get("last_temp") if pref else None
                old_hum = pref.get("last_humidity") if pref else None
                notify_result = maybe_notify_on_change(st.session_state['user_id'], st.session_state['email'],
                                                      city.strip(), old_temp, old_hum, w["temp"], w["humidity"])
                if notify_result:
                    st.info(notify_result)

                # Save/update preference and last observed weather
                save_user_pref(st.session_state['user_id'], city.strip(), w["temp"], w["humidity"])

    if st.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state['email'] = None
        st.rerun()

else:
    st.sidebar.header("Create account or login")
    choice = st.sidebar.selectbox("Action", ["Login", "Sign Up"])
    email = st.sidebar.text_input("Email")
    password = st.sidebar.text_input("Password", type="password")

    if choice == "Sign Up":
        if st.sidebar.button("Sign Up"):
            if not email or not password:
                st.sidebar.error("Enter email and password.")
            else:
                # validate email exists
                st.sidebar.info("Validating email...")
                ok = is_real_email(email)
                if not ok:
                    st.sidebar.error("Email validation failed — provide a real, non-disposable email.")
                else:
                    cursor.execute("SELECT id FROM users WHERE email=?", (email,))
                    if cursor.fetchone():
                        st.sidebar.error("Email already registered. Please login.")
                    else:
                        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
                        cursor.execute("INSERT INTO users(email, password_hash, signup_date) VALUES (?, ?, ?)",
                                       (email, pw_hash, str(datetime.now())))
                        conn.commit()
                        st.sidebar.success("Account created! Please login now.")

    elif choice == "Login":
        if st.sidebar.button("Login"):
            if not email or not password:
                st.sidebar.error("Enter email and password.")
            else:
                cursor.execute("SELECT id, password_hash FROM users WHERE email=?", (email,))
                user = cursor.fetchone()
                if user and bcrypt.checkpw(password.encode(), user[1]):
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = user[0]
                    st.session_state['email'] = email
                    cursor.execute("UPDATE users SET last_login=? WHERE id=?", (str(datetime.now()), user[0]))
                    conn.commit()
                    # After login, auto-check preferences and potentially send notification
                    pref = get_user_pref(user[0])
                    if pref and pref.get("city"):
                        w = get_weather(pref["city"])
                        if w:
                            # compare to stored last_temp/humidity and notify if needed
                            notify_result = maybe_notify_on_change(user[0], email, pref["city"],
                                                                  pref.get("last_temp"), pref.get("last_humidity"),
                                                                  w["temp"], w["humidity"])
                            if notify_result:
                                st.info("Auto-alert: " + notify_result)
                            # update last observed weather to current
                            save_user_pref(user[0], pref["city"], w["temp"], w["humidity"])
                    st.rerun()
                else:
                    st.sidebar.error("Invalid credentials.")

