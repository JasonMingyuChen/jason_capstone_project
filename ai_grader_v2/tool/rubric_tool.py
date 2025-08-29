from langchain_core.tools import tool
from utils.rubric_parser import parse_rubric
import streamlit as st
from api.canvas_api import get_assignment_rubric

@tool
def preview_rubric_tool(input_str: str) -> str:
    """Preview the rubric for a given course and assignment."""
    try:
        print(f"Preview rubric input: {input_str}")
        course_id, assignment_id = input_str.strip().split(",")
        course_id = course_id.strip()
        assignment_id = assignment_id.strip()
        print(f"Fetching rubric for course_id={course_id}, assignment_id={assignment_id}")
        
        # Update Streamlit state first
        st.session_state.course_id = course_id
        st.session_state.assignment_id = assignment_id
        
        # Then fetch the rubric
        rubric = get_assignment_rubric(course_id, assignment_id)
        if rubric:
            st.session_state.rubric_criteria = rubric
            # Format the rubric using parse_rubric
            formatted_rubric = parse_rubric(rubric)
            return f"Rubric Preview for Course {course_id}, Assignment {assignment_id}:\n\n{formatted_rubric}"
        return "No rubric found."
    except Exception as e:
        print(f"Error in preview_rubric_tool: {str(e)}")
        return f"Error previewing rubric: {str(e)}"

@tool
def load_rubric_tool(_: str) -> str:
    """Load the rubric from Streamlit session state into memory for grading."""
    if "rubric_criteria" in st.session_state:
        return "Rubric loaded successfully for grading."
    return "No rubric found. Please preview the rubric first."