from langchain_core.tools import tool
from api.canvas_api import get_submissions
import streamlit as st
import re
from bs4 import BeautifulSoup

def clean_html_text(html_content):
    """Clean HTML content and format it for readability."""
    if not html_content:
        return ""
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Get text while preserving some structure
    text = ""
    for element in soup.descendants:
        if element.name == 'h1':
            text += f"\n# {element.get_text().strip()}\n\n"
        elif element.name == 'h2':
            text += f"\n## {element.get_text().strip()}\n\n"
        elif element.name == 'h3':
            text += f"\n### {element.get_text().strip()}\n\n"
        elif element.name == 'p':
            text += f"{element.get_text().strip()}\n\n"
        elif element.name == 'br':
            text += "\n"
        elif element.name == 'ul' or element.name == 'ol':
            for li in element.find_all('li'):
                text += f"• {li.get_text().strip()}\n"
            text += "\n"
    
    # Clean up extra whitespace
    text = re.sub(r'\n\s*\n', '\n\n', text)
    text = text.strip()
    
    return text

@tool
def fetch_submission_tool(input_str: str) -> str:
    """Fetch submission for a specific course, assignment, and student."""
    try:
        course_id, assignment_id, student_id = input_str.strip().split(",")
        subs = get_submissions(course_id.strip(), assignment_id.strip())
        for sub in subs:
            if str(sub["user_id"]) == student_id.strip():
                # Clean and format the submission body
                raw_body = sub.get("body", "")
                formatted_body = clean_html_text(raw_body)
                
                # Store both raw and formatted versions
                st.session_state.selected_submission_body = raw_body  # Keep raw for grading
                st.session_state.formatted_submission_body = formatted_body  # Store formatted for display
                st.session_state.selected_student_name = sub.get("user", {}).get("name", "Unknown")
                st.session_state.selected_student_id = student_id.strip()
                
                return f"Submission from {st.session_state.selected_student_name}:\n\n{formatted_body}"
        return "Submission not found."
    except Exception as e:
        return f"Error fetching submission: {str(e)}"