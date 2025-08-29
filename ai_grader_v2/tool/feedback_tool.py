from langchain_core.tools import tool
from api.canvas_api import submit_grade_and_feedback
import streamlit as st

@tool
def submit_feedback_tool(_: str) -> str:
    """Submit the feedback and score to Canvas."""
    try:
        result = st.session_state.get("last_grade_result")
        if not result:
            return "No feedback to submit."

        course_id = st.session_state.get("course_id")
        assignment_id = st.session_state.get("assignment_id")
        student_id = st.session_state.get("selected_student_id")

        resp = submit_grade_and_feedback(
            course_id, assignment_id, student_id,
            result.get("score", 0), result.get("feedback", "")
        )
        return "Feedback submitted." if "error" not in resp else f"Submission error: {resp['error']}"
    except Exception as e:
        return f"Error submitting feedback: {str(e)}"