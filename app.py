import streamlit as st
import datetime
import os
from openai import OpenAI
from dotenv import load_dotenv
from calendar_utils import get_calendar_service, create_event
import pandas as pd
from dateutil import parser  
from datetime import timedelta


load_dotenv()

api_key = st.secrets.get("general", {}).get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=api_key)


st.title("Study Planner")

service = get_calendar_service()
if not service:
    st.info("Please authorize Google Calendar access to continue.")
    st.stop()
else:
    st.success("Connected to Google Calendar!")

subject = st.text_input("Subject (required)")
study_guide = st.text_area("Paste your study guide (optional)")
test_date = st.date_input("Date of Test", min_value=datetime.date.today())
weekday_hours = st.number_input("Hours available on weekdays", 1, 6, 2)
weekend_hours = st.number_input("Hours available on weekends", 1, 12, 4)

start_date = datetime.date.today()
days_list = []
for i in range((test_date - start_date).days + 1):
    d = start_date + timedelta(days=i)
    days_list.append(f"{d.strftime('%Y-%m-%d (%A)')}")
available_days = "\n".join(days_list)

if st.button("Generate Schedule"):
    if not subject:
        st.error("Please enter a subject")
    else:
        days_left = (test_date - datetime.date.today()).days

        prompt = f"""
        You are a study planning assistant. 
        Subject: {subject}
        Test date: {test_date}
        Days left: {days_left}
        
        Here are the available days before the test:
        {available_days}

        Each of Sunday, Monday, Tuesday, Wednesday, and Thursday can have up to {weekday_hours} study hours,
        and Friday and Saturday can have up to {weekend_hours} study hours.

        Study guide: {study_guide if study_guide else "None"}

        Please return the study schedule in **Markdown format** with this style:
        - A title for the schedule
        - A short intro line
        - A table with columns: Date | Hours (limited by values specified above by day; check if each day is a weekday or weekend, then assign hours based on that) | Topics (max length 15 words, list specific topics even if not provided; use general knowledge of the subject to divide topics into reasonable chunks)
        - At the end, a motivational closing note

        The order of study topics should be logical and progressive.

        Make sure it looks clean and easy to read.

        Do NOT use any emojis or special characters.
        Do NOT include any explanations outside the Markdown.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You format schedules in neat Markdown tables."},
                    {"role": "user", "content": prompt},
                ]
            )

            st.session_state["plan_md"] = response.choices[0].message.content

        except Exception as e:
            st.error(f"Error: {str(e)}")

if "plan_md" in st.session_state:
    plan_md = st.session_state["plan_md"]
    st.markdown(plan_md, unsafe_allow_html=True)

    if st.checkbox("Add this schedule to Google Calendar"):
        rows = []
        lines = plan_md.splitlines()

        for line in lines:
            if "|" in line and "Date" not in line and "---" not in line:
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if len(parts) >= 3:
                    date_str, hours, topic = parts[0], parts[1], parts[2]
                    try:
                        date = parser.parse(date_str).date()
                        rows.append((date, hours, topic))
                    except:
                        continue

        if rows:
            df = pd.DataFrame(rows, columns=["Date", "Hours", "Topic"])
            st.write("Events to be added:", df)

            if st.button("Confirm and Add to Calendar"):
                for _, row in df.iterrows():
                    create_event(service, subject, row["Date"], row["Hours"], row["Topic"])
                st.success("Study sessions added to your Google Calendar!")
        else:
            st.warning("Could not parse schedule into events. Please check the table format.")
