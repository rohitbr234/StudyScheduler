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
        redirect_uri = "https://rohitbr234-studyscheduler-app-kcvmpe.streamlit.app"

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
            
            st.info(f"🔄 Processing authorization code... (length: {len(code)})")
            
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            st.session_state["google_creds"] = creds
            
            if "oauth_flow" in st.session_state:
                del st.session_state["oauth_flow"]
            if "flow_redirect_uri" in st.session_state:
                del st.session_state["flow_redirect_uri"]
            
            st.query_params.clear()
            st.success("✅ Authentication successful!")
            st.rerun()
            
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ Authentication failed: {error_msg}")
            
            with st.expander("🔍 Debug Information - Please share this"):
                st.write(f"**Error type:** {type(e).__name__}")
                st.write(f"**Full error:** {error_msg}")
                st.write(f"**Redirect URI:** `{redirect_uri}`")
                st.write(f"**Code length:** {len(code) if 'code' in locals() else 'N/A'}")
                st.write(f"**Running locally:** {running_locally}")
                
                if not running_locally:
                    st.write("**Secrets keys:**", list(st.secrets.get("gcp_oauth", {}).keys()))
                
                st.write("---")
                st.write("**Common causes:**")
                st.write("1. Redirect URI mismatch in Google Cloud Console")
                st.write("2. Using 'Desktop app' instead of 'Web application' client type")
                st.write("3. Authorization code used twice (try authorizing again)")
                st.write("4. Authorization code expired (valid for ~10 minutes)")
            
            st.query_params.clear()
            if "oauth_flow" in st.session_state:
                del st.session_state["oauth_flow"]
            if "flow_redirect_uri" in st.session_state:
                del st.session_state["flow_redirect_uri"]
            
            st.info("Click the authorization link below to try again")
            return None

    auth_url, state = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )
    
    st.warning("🔐 **Authorization Required**")
    st.write("Please click the link below to authorize Google Calendar access:")
    st.markdown(f"### [🔗 Authorize Google Calendar Access]({auth_url})")
    
    with st.expander("ℹ️ Troubleshooting"):
        st.write("**If you see 'Malformed auth code' error:**")
        st.write("1. Verify in Google Cloud Console:")
        st.write(f"   - Client type is **Web application** (not Desktop app)")
        st.write(f"   - Authorized redirect URI is exactly: `{redirect_uri}`")
        st.write("2. Wait 5 minutes after changing settings in Google Cloud Console")
        st.write("3. Try authorizing in an incognito/private browser window")
        st.write("4. Make sure you're not reusing an old authorization link")
    
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
