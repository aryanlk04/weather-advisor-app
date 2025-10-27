from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import streamlit as st

SENDGRID_API_KEY = st.secrets["SENDGRID_API_KEY"]
SENDER_EMAIL = st.secrets.get("SENDER_EMAIL")  # sender email e.g. "no-reply@yourdomain.com"
SENDER_NAME = st.secrets.get("SENDER_NAME", "Health Advisor")

def send_health_email(to_email, subject, plain_text):
    """
    Send an email via SendGrid. Returns True on success.
    """
    message = Mail(
        from_email=(SENDER_EMAIL, SENDER_NAME),
        to_emails=to_email,
        subject=subject,
        plain_text_content=plain_text
    )
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        # success codes 200-299
        return 200 <= response.status_code < 300
    except Exception as e:
        print("SendGrid error:", e)
        return False