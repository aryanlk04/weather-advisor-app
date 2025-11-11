import streamlit as st
import sqlite3
import bcrypt
from datetime import datetime
from twilio.rest import Client
from weather_utils import get_weather, health_advice   # you already have this

# -------------------- PAGE CONFIG --------------------
st.set_page_config(page_title="Dream Aware", page_icon="🩺", layout="centered")

# -------------------- TWILIO (from secrets) --------------------
# Add these to .streamlit/secrets.toml:
# TWILIO_SID = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# TWILIO_AUTH = "your_auth_token"
# TWILIO_VERIFY_SID = "VAxxxxxxxxxxxxxxxxxxxxxxxx"  # Verify Service SID
def get_twilio_client():
    return Client(st.secrets["TWILIO_SID"], st.secrets["TWILIO_AUTH"])

VERIFY_SID = st.secrets.get("TWILIO_VERIFY_SID", None)

# -------------------- DB SETUP --------------------
conn = sqlite3.connect("database.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT UNIQUE NOT NULL,
    address TEXT,
    password_hash BLOB NOT NULL,
    verified INTEGER DEFAULT 0,
    signup_date TEXT,
    last_login TEXT
)
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS preferences(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    city TEXT,
    FOREIGN KEY(user_id) REFERENCES users(id)
)
""")
conn.commit()

# -------------------- SESSION --------------------
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.email = None
if "signup_stage" not in st.session_state:
    st.session_state.signup_stage = "form"  # form -> otp
if "pending_user" not in st.session_state:
    st.session_state.pending_user = None  # temp store before OTP

# -------------------- NAV --------------------
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 Home", use_container_width=True): st.session_state.page = "Home"
with col2:
    if st.button("ℹ️ About", use_container_width=True): st.session_state.page = "About"
with col3:
    if st.button("📞 Contact", use_container_width=True): st.session_state.page = "Contact"
st.write("---")

# -------------------- HELPERS --------------------
def email_or_phone_login(login_id: str, password: str):
    cur.execute("SELECT id, password_hash, verified, email FROM users WHERE email=? OR phone=?", (login_id, login_id))
    row = cur.fetchone()
    if not row:
        return False, "User not found."
    uid, pw_hash, verified, email = row
    if not verified:
        return False, "Your account is not verified yet. Please sign up and complete OTP verification."
    if bcrypt.checkpw(password.encode(), pw_hash):
        st.session_state.logged_in = True
        st.session_state.user_id = uid
        st.session_state.email = email
        cur.execute("UPDATE users SET last_login=? WHERE id=?", (str(datetime.now()), uid))
        conn.commit()
        return True, None
    return False, "Incorrect password."

def send_verify_code(phone: str) -> bool:
    """Send an OTP via Twilio Verify to the given phone."""
    if not VERIFY_SID:
        st.error("Twilio Verify SID not configured. Add TWILIO_VERIFY_SID to secrets.")
        return False
    client = get_twilio_client()
    try:
        client.verify.v2.services(VERIFY_SID).verifications.create(to=phone, channel="sms")
        return True
    except Exception as e:
        st.error(f"Failed to send OTP: {e}")
        return False

def check_verify_code(phone: str, code: str) -> bool:
    """Validate the OTP via Twilio Verify."""
    client = get_twilio_client()
    try:
        res = client.verify.v2.services(VERIFY_SID).verification_checks.create(to=phone, code=code.strip())
        return res.status == "approved"
    except Exception as e:
        st.error(f"Verification failed: {e}")
        return False

# -------------------- PAGES --------------------
if st.session_state.page == "Home":
    st.title("🩺 Dream Aware")
    st.subheader("Weather-Based Health Advisory System")

    if st.session_state.logged_in:
        st.success(f"Welcome back, {st.session_state.email}!")
        city = st.text_input("🏙️ Enter your city:")
        if st.button("Check Health Advice"):
            if not city.strip():
                st.warning("Please enter a city.")
            else:
                w = get_weather(city.strip())
                if not w:
                    st.error("City not found or API error.")
                else:
                    c1, c2 = st.columns(2)
                    with c1:
                        st.metric("🌡 Temperature (°C)", w["temp"])
                        st.metric("💧 Humidity (%)", w["humidity"])
                    with c2:
                        st.info(f"☁️ Condition: {w['condition'].capitalize()}")
                    st.subheader("💡 Health Recommendations")
                    for tip in health_advice(w["temp"], w["humidity"], w["condition"]):
                        st.success(tip)

                    # save preferred city
                    cur.execute("SELECT 1 FROM preferences WHERE user_id=?", (st.session_state.user_id,))
                    if cur.fetchone():
                        cur.execute("UPDATE preferences SET city=? WHERE user_id=?", (city.strip(), st.session_state.user_id))
                    else:
                        cur.execute("INSERT INTO preferences(user_id, city) VALUES (?,?)", (st.session_state.user_id, city.strip()))
                    conn.commit()

        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.email = None
            st.rerun()

    else:
        tab_login, tab_signup = st.tabs(["🔑 Login", "🆕 Sign Up"])

        # -------- LOGIN --------
        with tab_login:
            login_id = st.text_input("Email or Phone Number")
            password = st.text_input("Password", type="password")
            if st.button("Login"):
                ok, msg = email_or_phone_login(login_id.strip(), password)
                if ok:
                    st.rerun()
                else:
                    st.error(msg)

       # ---------- SIGN UP (FORM -> OTP) ----------
with tab_signup:
    # init stage flags
   
    if st.session_state.signup_stage == "form":
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        phone = st.text_input("Phone (E.164, e.g., +9190xxxxxxx)")
        address = st.text_area("Address")
        pw = st.text_input("Create Password", type="password")

        if st.button("Send OTP", key="send_otp_btn"):
            if not all([name.strip(), email.strip(), phone.strip(), pw.strip()]):
                st.warning("Please fill all required fields (name, email, phone, password).")
            else:
                # check duplicates
                cur.execute("SELECT 1 FROM users WHERE email=? OR phone=?", (email.strip(), phone.strip()))
                if cur.fetchone():
                    st.error("An account with this email/phone already exists.")
                else:
                    # send code via Twilio Verify
                    if send_verify_code(phone.strip()):
                        # stash user info until OTP is verified
                        st.session_state.pending_user = {
                            "name": name.strip(),
                            "email": email.strip(),
                            "phone": phone.strip(),
                            "address": address.strip(),
                            "password": pw
                        }
                        st.session_state.signup_stage = "otp"
                        st.success(f"OTP sent to {phone}. Please enter it below.")
                        st.experimental_rerun()   # <-- force UI to show OTP inputs immediately

    elif st.session_state.signup_stage == "otp":
        st.info(f"Enter the OTP sent to {st.session_state.pending_user['phone']}")
        code = st.text_input("Verification code (6 digits)", max_chars=6, key="otp_code")

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Verify & Create Account", key="verify_btn"):
                if not code.strip():
                    st.warning("Please enter the OTP.")
                else:
                    pu = st.session_state.pending_user
                    if pu and check_verify_code(pu["phone"], code):
                        pw_hash = bcrypt.hashpw(pu["password"].encode(), bcrypt.gensalt())
                        cur.execute(
                            "INSERT INTO users(name,email,phone,address,password_hash,verified,signup_date) "
                            "VALUES (?,?,?,?,?,?,?)",
                            (pu["name"], pu["email"], pu["phone"], pu["address"], pw_hash, 1, str(datetime.now()))
                        )
                        conn.commit()
                        st.success("✅ Phone verified & account created! Please log in.")
                        # reset state
                        st.session_state.signup_stage = "form"
                        st.session_state.pending_user = None
                        st.rerun()
                    else:
                        st.error("Invalid or Expired OTP. Try Again.")

        with c2:
            if st.button("Resend OTP", key="resend_btn"):
                pu = st.session_state.pending_user
                if pu and send_verify_code(pu["phone"]):
                    st.info("OTP resent. Please check your messages.")

        with c3:
            if st.button("Cancel", key="cancel_btn"):
                st.session_state.signup_stage = "form"
                st.session_state.pending_user = None
                st.rerun()

if st.session_state.page == "About":
    st.title("ℹ️ About Dream Aware")
    st.write(
        "Dream Aware is a weather-based health advisory system. It combines real-time "
        "weather from OpenWeather with practical health guidance, and includes secure "
        "OTP-verified accounts (Twilio Verify)."
    )

elif st.session_state.page == "Contact":
    st.title("📞 Contact")
    st.write("Phone: **90195 31192**\n\nEmail: **support@dreamaware.ai**")

st.markdown("<hr><center>© 2025 Dream Aware — Weather-Based Health Advisor</center>", unsafe_allow_html=True)



