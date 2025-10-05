from __future__ import print_function
import os
import datetime
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

# Google Calendar scope
SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    """
    Authenticate user with Google Calendar and return a service object.
    Uses Streamlit session_state to persist credentials per user.
    """
    creds = st.session_state.get("google_creds")

    # If credentials already exist and are valid → return service
    if creds and creds.valid:
        return build("calendar", "v3", credentials=creds)

    # If expired but refreshable → refresh and save
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        st.session_state["google_creds"] = creds
        return build("calendar", "v3", credentials=creds)

    # Otherwise start OAuth flow
    flow = Flow.from_client_secrets_file(
        "credentials.json",
        scopes=SCOPES,
        redirect_uri="http://localhost:8501"  # replace with deployed URL later
    )

    # Check if Google redirected back with a "code"
    query_params = st.query_params
    if "code" in query_params:
        code = query_params["code"]
        code = code.strip()

        try:
            flow.fetch_token(code=code)
            creds = flow.credentials
            st.session_state["google_creds"] = creds
            
            # Clear the query params to prevent reuse
            st.query_params.clear()
            
            return build("calendar", "v3", credentials=creds)
        
        except Exception as e:
            st.error(f"Authentication failed: {str(e)}")
            st.query_params.clear()  # Clear params on error
            return None

    # Otherwise → show login link
    auth_url, _ = flow.authorization_url(prompt="consent")
    st.markdown(f"[Click here to authorize Google Calendar access]({auth_url})")
    return None

def create_event(service, subject, date, hours, topic, start_hour=18):
    """
    Creates a study session event in the user's Google Calendar.
    Default start time is 6PM local time unless overridden.
    """
    start_time = datetime.datetime.combine(date, datetime.time(start_hour, 0))
    end_time = start_time + datetime.timedelta(hours=int(hours))

    event = {
        "summary": f"Study: {subject}",
        "description": topic,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/New_York"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/New_York"},
    }
    return service.events().insert(calendarId="primary", body=event).execute()
