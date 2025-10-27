import requests
import streamlit as st

EMAIL_VALIDATION_KEY = st.secrets["EMAIL_VALIDATION_KEY"]

def is_real_email(email):
    """
    Uses Abstract Email Validation API to check mailbox.
    Returns True if email seems real (format ok, smtp check true, not disposable).
    """
    try:
        url = "https://emailvalidation.abstractapi.com/v1/"
        params = {"api_key": EMAIL_VALIDATION_KEY, "email": email}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        # Key fields: is_valid_format, is_smtp_valid, is_disposable_email.value
        valid_format = data.get("is_valid_format", {}).get("value", False)
        smtp_valid = data.get("is_smtp_valid", {}).get("value", False)
        disposable = data.get("is_disposable_email", {}).get("value", False)
        # Consider domain existence also (optional)
        return bool(valid_format and smtp_valid and not disposable)
    except Exception as e:
        print("Email validation error:", e)
        # If validation service fails, default to False to avoid fake accounts
        return False