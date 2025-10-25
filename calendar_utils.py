from __future__ import print_function
import os
import datetime
import streamlit as st
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]

def get_calendar_service():
    creds = st.session_state.get("google_creds")

    if creds and creds.valid:
        return build("calendar", "v3", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            st.session_state["google_creds"] = creds
            return build("calendar", "v3", credentials=creds)
        except Exception as e:
            st.error(f"Token refresh failed: {e}")
            del st.session_state["google_creds"]

    running_locally = os.path.exists("credentials.json")

    if running_locally:
        redirect_uri = "http://localhost:8501"
    else:
        redirect_uri = "https://studyscheduler.streamlit.app"

    if "oauth_flow" not in st.session_state or st.session_state.get("flow_redirect_uri") != redirect_uri:
        if running_locally:
            flow = Flow.from_client_secrets_file(
                "credentials.json",
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
        else:
            client_config = {
                "web": {
                    "client_id": st.secrets["gcp_oauth"]["client_id"],
                    "client_secret": st.secrets["gcp_oauth"]["client_secret"],
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [redirect_uri]
                }
            }
            flow = Flow.from_client_config(
                client_config,
                scopes=SCOPES,
                redirect_uri=redirect_uri
            )
        
        st.session_state["oauth_flow"] = flow
        st.session_state["flow_redirect_uri"] = redirect_uri
    else:
        flow = st.session_state["oauth_flow"]

    query_params = st.query_params
    
    if "code" in query_params:
        try:
            code = query_params.get("code")
            if isinstance(code, list):
                code = code[0]
            
            code = str(code).strip()
            
            with st.spinner("🔄 Connecting to Google Calendar..."):
                flow.fetch_token(code=code)
                creds = flow.credentials
                
                st.session_state["google_creds"] = creds
                
                if "oauth_flow" in st.session_state:
                    del st.session_state["oauth_flow"]
                if "flow_redirect_uri" in st.session_state:
                    del st.session_state["flow_redirect_uri"]
                
                st.query_params.clear()
                st.success("✅ Successfully connected to Google Calendar!")
                st.rerun()
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Connection failed: {error_msg}")
            
            with st.expander("🔍 Debug Information"):
                st.code(f"""
Error Type: {type(e).__name__}
Error Message: {error_msg}
Redirect URI: {redirect_uri}
Code Length: {len(code) if 'code' in locals() else 'N/A'}
Running Locally: {running_locally}
                """)
            
            st.query_params.clear()
            if "oauth_flow" in st.session_state:
                del st.session_state["oauth_flow"]
            if "flow_redirect_uri" in st.session_state:
                del st.session_state["flow_redirect_uri"]
            
            return None

    # Generate authorization URL
    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )
    
    # Clean, minimal authorization UI
    st.markdown(f"""
        <style>
        .auth-box {{
            background: white;
            border-radius: 12px;
            padding: 2.5rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            text-align: center;
            max-width: 600px;
            margin: 3rem auto;
        }}
        .auth-icon {{
            font-size: 3.5rem;
            margin-bottom: 1rem;
        }}
        .auth-heading {{
            font-size: 1.75rem;
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 0.75rem;
        }}
        .auth-description {{
            font-size: 1rem;
            color: #6b7280;
            margin-bottom: 2rem;
            line-height: 1.6;
        }}
        .auth-button {{
            display: inline-block;
            background: #4285f4 !important;
            color: white !important;
            padding: 14px 32px;
            border-radius: 8px;
            text-decoration: none !important;
            font-weight: 600;
            font-size: 1.1rem;
            transition: all 0.2s;
            box-shadow: 0 2px 8px rgba(66, 133, 244, 0.3);
            border: none;
        }}
        .auth-button:hover {{
            background: #3367d6 !important;
            box-shadow: 0 4px 12px rgba(66, 133, 244, 0.4);
            transform: translateY(-1px);
            color: white !important;
            text-decoration: none !important;
        }}
        .auth-button:visited {{
            color: white !important;
        }}
        .security-note {{
            margin-top: 2rem;
            padding: 1rem;
            background: #f3f4f6;
            border-radius: 8px;
            font-size: 0.9rem;
            color: #6b7280;
        }}
        </style>
        
        <div class="auth-box">
            <div class="auth-icon">🗓️</div>
            <div class="auth-heading">Connect Your Google Calendar</div>
            <div class="auth-description">
                To create and manage study sessions, we need permission to access your Google Calendar.
                This is a secure, one-time authorization.
            </div>
            <a href="{auth_url}" class="auth-button" target="_self">
                ✓ Connect Google Calendar
            </a>
            <div class="security-note">
                🔒 Your data is secure. We only request calendar access and never store your credentials.
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    return None


def create_event(service, subject, date, hours, topic, start_hour=18):
    start_time = datetime.datetime.combine(date, datetime.time(start_hour, 0))
    end_time = start_time + datetime.timedelta(hours=int(hours))

    event = {
        "summary": f"Study: {subject}",
        "description": topic,
        "start": {"dateTime": start_time.isoformat(), "timeZone": "America/New_York"},
        "end": {"dateTime": end_time.isoformat(), "timeZone": "America/New_York"},
    }

    return service.events().insert(calendarId="primary", body=event).execute()