from langchain_core.tools import tool
from api.canvas_api import submit_grade_and_feedback
import streamlit as st


@tool
def submit_tool(_: str) -> str:
    """Submit the final grade and feedback to Canvas."""
    try:
        course_id = st.session_state.get("course_id")
        assignment_id = st.session_state.get("assignment_id")
        student_id = st.session_state.get("selected_student_id")
        final_score = st.session_state.get("final_score")
        feedback = st.session_state.get("final_feedback")

        if not all([course_id, assignment_id, student_id, final_score, feedback]):
            return "Missing course ID, assignment ID, student ID, score, or feedback."

        result = submit_grade_and_feedback(
            course_id, assignment_id, student_id, final_score, feedback
        )

        if "error" in result:
            return f"Failed to submit to Canvas: {result['error']}"

        return f"Grade and feedback successfully submitted to Canvas."
    except Exception as e:
        return f"Error during submission: {e}"