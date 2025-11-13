# send_alerts.py
import sqlite3
import time
import requests
import os
from datetime import datetime
from twilio.rest import Client
from weather_utils import get_weather, health_advice  # reuse your module

# ---------------- Configuration (read from environment / GitHub secrets) ----------------
TWILIO_SID = os.environ.get("TWILIO_SID")
TWILIO_AUTH = os.environ.get("TWILIO_AUTH")
TWILIO_PHONE = os.environ.get("TWILIO_PHONE")  # the Twilio sender (from_)
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@dreamaware.app")  # for email 'from'
DB_FILE = os.environ.get("DB_FILE", "database.db")

# ---------------- Helpers ----------------
def send_sms(to_phone: str, body: str) -> bool:
    if not (TWILIO_SID and TWILIO_AUTH and TWILIO_PHONE):
        print("Twilio credentials missing; skipping SMS.")
        return False
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH)
        msg = client.messages.create(body=body, from_=TWILIO_PHONE, to=to_phone)
        print(f"SMS sent to {to_phone} sid={msg.sid}")
        return True
    except Exception as e:
        print(f"Failed to send SMS to {to_phone}: {e}")
        return False

def send_email(to_email: str, subject: str, body: str) -> bool:
    if not SENDGRID_API_KEY:
        print("SendGrid API key missing; skipping email.")
        return False
    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {SENDGRID_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "personalizations": [
            { "to": [{"email": to_email}], "subject": subject }
        ],
        "from": {"email": FROM_EMAIL, "name": "Dream Aware"},
        "content": [
            {"type": "text/plain", "value": body},
            {"type": "text/html", "value": body.replace("\n", "<br>")}
        ]
    }
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=20)
        if r.status_code in (200, 202):
            print(f"Email sent to {to_email}")
            return True
        else:
            print(f"SendGrid error {r.status_code}: {r.text}")
            return False
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return False

def build_alert_message(name: str, city: str, w: dict) -> (str, str):
    """
    Builds detailed plain-text subject and body for the alert.
    w is expected: {"temp":..., "humidity":..., "condition":...}
    """
    temp = w.get("temp")
    hum = w.get("humidity")
    cond = w.get("condition", "Unknown").capitalize()
    advice_list = health_advice(temp, hum, cond)

    subject = f"Daily Health Alert — {city} — {cond}, {temp}°C"
    body_lines = [
        f"Hello {name},",
        "",
        f"Here is your daily weather & health advisory for {city} ({datetime.now().strftime('%Y-%m-%d %H:%M')}):",
        f"- Condition: {cond}",
        f"- Temperature: {temp} °C",
        f"- Humidity: {hum} %",
        ""
    ]
    body_lines.append("Personalized health recommendations:")
    for tip in advice_list:
        body_lines.append(f"- {tip}")
    body_lines.append("")
    # Add practical detailed guidance
    body_lines.append("Detailed guidance:")
    # Example expansions — you can customize or expand
    if temp is not None:
        if temp >= 35:
            body_lines.append("• High temperature: Stay in shade, avoid strenuous outdoor exercise between 11am-4pm, drink extra water (at least 3-4 liters), and consider electrolyte drinks if active.")
        elif temp <= 10:
            body_lines.append("• Low temperature: Wear layered clothing, limit exposure to cold, and keep warm indoors to avoid hypothermia or flu risk.")
        else:
            body_lines.append("• Moderate temperature: Maintain normal activity but stay hydrated and take breaks in shade if outdoors.")

    if hum is not None:
        if hum >= 80:
            body_lines.append("• High humidity: Body cooling is less efficient. Avoid heavy exertion outside; indoor cooling or fans help.")
        elif hum <= 30:
            body_lines.append("• Low humidity: Skin and nasal passages may dry. Use moisturizers and drink water frequently.")
    # condition-specific
    if cond:
        lc = cond.lower()
        if "rain" in lc:
            body_lines.append("• Rain expected: carry an umbrella, wear water-resistant clothing, avoid standing water to prevent infections.")
        if "clear" in lc or "sun" in lc:
            body_lines.append("• Sun/UV: Use sunscreen (SPF 30+), wear sunglasses and hats during peak sunlight hours.")
        if "smog" in lc or "haze" in lc or "dust" in lc:
            body_lines.append("• Poor air quality: Use N95 masks outdoors, limit outdoor activities, and keep windows closed.")

    body_lines.append("")
    body_lines.append("Stay safe — Dream Aware")
    body_text = "\n".join(body_lines)
    return subject, body_text

# ---------------- Main routine ----------------
def main():
    print("Starting daily alerts job:", datetime.now().isoformat())
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Join users and preferences; if user has no saved city skip (or optionally fetch last city)
    cur.execute("""
        SELECT u.id, u.name, u.email, u.phone, u.verified, p.city
        FROM users u
        LEFT JOIN preferences p ON p.user_id = u.id
        WHERE u.verified = 1
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} verified users")

    for uid, name, email, phone, verified, city in rows:
        if not city:
            print(f"User {uid} ({name}) has no saved city — skipping")
            continue
        try:
            w = get_weather(city)  # use your existing function
            if not w:
                print(f"Weather fetch failed for {city}; skipping user {name}")
                continue

            subject, body = build_alert_message(name or "User", city, w)
            sent_any = False

            # Prefer SMS if phone exists
            if phone:
                # send SMS (keep SMS shorter)
                sms_body = f"{subject}\n\n" + "\n".join(line for line in body.splitlines()[:8])
                ok = send_sms(phone, sms_body)
                sent_any = sent_any or ok
                # slight pause to avoid rate limits
                time.sleep(1)

            # Also send email if email exists
            if email:
                ok = send_email(email, subject, body)
                sent_any = sent_any or ok
                time.sleep(1)

            if sent_any:
                print(f"Alert delivered to user id={uid} ({name})")
            else:
                print(f"Failed to deliver alert to user id={uid} ({name})")
        except Exception as e:
            print(f"Error processing user {uid}: {e}")

    conn.close()
    print("Daily alerts job finished at:", datetime.now().isoformat())

if __name__ == "__main__":
    main()