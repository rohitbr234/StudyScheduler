import streamlit as st
import datetime
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

st.title("Study Planner")

subject = st.text_input("Subject (required)")
study_guide = st.text_area("Paste your study guide (optional)")
test_date = st.date_input("Date of Test", min_value=datetime.date.today())
weekday_hours = st.number_input("Hours available on weekdays", 1, 6, 2)
weekend_hours = st.number_input("Hours available on weekends", 1, 12, 4)

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
        Hours available on weekdays: {weekday_hours}
        Hours available on weekends: {weekend_hours}
        Study guide: {study_guide if study_guide else "None"}

        Please return the study schedule in **Markdown format** with this style:
        - A title for the schedule
        - A short intro line
        - A table with columns: Date | Hours | Topics
        - At the end, a motivational closing note

        Make sure it looks clean and easy to read.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You format schedules in neat Markdown tables."},
                    {"role": "user", "content": prompt},
                ]
            )

            plan_md = response.choices[0].message.content
            st.subheader("Generated Study Schedule")
            st.markdown(plan_md, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Error: {str(e)}")
