from langchain_core.tools import tool
import streamlit as st
from utils.rubric_parser import parse_rubric
from utils.llm_utils import strict_grading_llm
from api.canvas_api import get_assignment_rubric, get_submissions, submit_grade_and_feedback
import json
from functools import wraps

def _ensure_state_persistence(func):
    """Decorator to ensure state is preserved between tool calls."""
    @wraps(func)  # This preserves the original function's metadata
    def wrapper(input_str: str = "") -> str:
        # Parse input string for IDs if provided
        course_id = None
        assignment_id = None
        student_id = None
        
        if "," in input_str:
            try:
                course_id, assignment_id, student_id = input_str.strip().split(",")
                course_id = course_id.strip()
                assignment_id = assignment_id.strip()
                student_id = student_id.strip()
                # Store in session state
                st.session_state.course_id = course_id
                st.session_state.assignment_id = assignment_id
                st.session_state.student_id = student_id
            except ValueError:
                pass
        
        # Always try to get from session state if not in input
        if not all([course_id, assignment_id, student_id]):
            course_id = st.session_state.get("course_id")
            assignment_id = st.session_state.get("assignment_id")
            student_id = st.session_state.get("student_id")
        
        # Store the IDs back in session state
        if all([course_id, assignment_id, student_id]):
            st.session_state.course_id = course_id
            st.session_state.assignment_id = assignment_id
            st.session_state.student_id = student_id
        
        return func(input_str)
    return wrapper

@tool
def grade_selected_tool(input_str: str = "") -> str:
    """Grade the selected submission using the loaded rubric.
    
    Args:
        input_str: Optional comma-separated string of course_id, assignment_id, student_id
        
    Returns:
        str: Grading result with score and feedback
    """
    try:
        # Parse input string for IDs if provided
        course_id = None
        assignment_id = None
        student_id = None
        
        # First try to parse from input string
        if input_str:
            try:
                if "," in input_str:
                    course_id, assignment_id, student_id = input_str.strip().split(",")
                else:
                    # Try to parse from the input string format "student XXX in course YYY, assignment ZZZ"
                    parts = input_str.lower().split()
                    for i, part in enumerate(parts):
                        if part == "student" and i + 1 < len(parts):
                            student_id = parts[i + 1]
                        elif part == "course" and i + 1 < len(parts):
                            course_id = parts[i + 1].rstrip(",")
                        elif part == "assignment" and i + 1 < len(parts):
                            assignment_id = parts[i + 1]
                
                # Clean up any extracted IDs
                if course_id: course_id = course_id.strip()
                if assignment_id: assignment_id = assignment_id.strip()
                if student_id: student_id = student_id.strip()
            except ValueError:
                pass
        
        # If any ID is missing, try session state
        if not all([course_id, assignment_id, student_id]):
            course_id = st.session_state.get("course_id") or course_id
            assignment_id = st.session_state.get("assignment_id") or assignment_id
            student_id = st.session_state.get("student_id") or student_id
        
        # Store valid IDs in session state
        if course_id: st.session_state.course_id = course_id
        if assignment_id: st.session_state.assignment_id = assignment_id
        if student_id: st.session_state.student_id = student_id
        
        print(f"Processing with IDs - course: {course_id}, assignment: {assignment_id}, student: {student_id}")
        
        if not all([course_id, assignment_id, student_id]):
            return "Missing required information. Please provide course_id, assignment_id, and student_id."
        
        # Get or fetch submission content
        submission_body = st.session_state.get("selected_submission_body")
        if not submission_body:
            print(f"Fetching submission for student {student_id}")
            # Fetch submission
            subs = get_submissions(course_id, assignment_id)
            submission_found = False
            for sub in subs:
                if str(sub["user_id"]) == student_id:
                    submission_body = sub.get("body", "")
                    st.session_state.selected_submission_body = submission_body
                    st.session_state.selected_student_name = sub.get("user", {}).get("name", "Unknown")
                    submission_found = True
                    break
            
            if not submission_found:
                return "No submission found for the specified student."

        # Get formatted submission for better readability
        formatted_submission = st.session_state.get("formatted_submission_body", submission_body)
        
        # Try to get rubric from different sources
        rubric = None
        
        # 1. First check if we have an uploaded rubric
        if "uploaded_rubric" in st.session_state:
            print("Attempting to use uploaded rubric")
            try:
                uploaded = st.session_state.uploaded_rubric
                if isinstance(uploaded, str):
                    rubric = json.loads(uploaded)
                else:
                    rubric = uploaded
                print("Successfully loaded uploaded rubric")
            except json.JSONDecodeError:
                print("Failed to parse uploaded rubric")
                pass

        # 2. If not, check if we have a rubric in session state
        if not rubric and "rubric_criteria" in st.session_state:
            print("Using rubric from session state")
            rubric = st.session_state.rubric_criteria
        
        # 3. If still not found, try to fetch from Canvas
        if not rubric:
            print(f"Fetching rubric from Canvas for course {course_id}, assignment {assignment_id}")
            rubric = get_assignment_rubric(course_id, assignment_id)
            if rubric:
                print("Successfully fetched rubric from Canvas")
                st.session_state.rubric_criteria = rubric
        
        # 4. If still no rubric, use default basic rubric
        if not rubric:
            print("No rubric found, proceeding with basic grading")
            rubric = [{
                "description": "Overall Assessment",
                "points": 100,
                "long_description": "Evaluate the submission based on:\n- Content quality and depth\n- Organization and clarity\n- Evidence and support\n- Writing mechanics and style",
                "ratings": [
                    {"description": "Excellent", "points": 100},
                    {"description": "Good", "points": 85},
                    {"description": "Fair", "points": 70},
                    {"description": "Poor", "points": 55}
                ]
            }]
        
        # Parse rubric into a clean format
        parsed_criteria = parse_rubric(rubric)
        
        # Grade the submission
        print("Starting grading process")
        result = strict_grading_llm(formatted_submission, parsed_criteria)
        print("Grading completed")
        
        # Store the result for later use
        st.session_state.last_grade_result = result
        
        # Format the grading result
        if isinstance(result, dict):
            feedback = result.get("feedback", "")
            
            # Better score parsing
            try:
                # Try to extract score from the feedback first line
                first_line = feedback.split('\n')[0]
                if 'Score:' in first_line or 'Overall Score:' in first_line:
                    score = float(first_line.split(':')[1].split('/')[0].strip())
                else:
                    score = result.get("score", 0)
            except:
                score = result.get("score", 0)
            
            student_name = st.session_state.get("selected_student_name", "Unknown Student")
            
            # Store current grade and feedback for later use
            st.session_state.current_grade = score
            st.session_state.current_feedback = feedback
            
            # Create response with next steps
            response = [
                f"Grade for {student_name}:",
                f"Score: {score}/100",
                "\nFeedback:",
                feedback,
                "\nNext Steps:",
                "1. To modify the grade, type: 'modify grade score: XX'",
                "2. To modify feedback, type: 'modify grade feedback: your new feedback'",
                "3. To submit this grade to Canvas, type: 'submit grade to canvas'",
                "4. To grade another submission, provide a new student ID"
            ]
            
            return "\n".join(response)
        else:
            return str(result)
            
    except Exception as e:
        print(f"Error in grade_selected_tool: {str(e)}")
        return f"Grading failed: {str(e)}"

@tool
def modify_grade_tool(input_str: str = "") -> str:
    """Modify the grade score for the last graded submission.
    
    Args:
        input_str: Command string in format 'score: XX'
        
    Returns:
        str: Confirmation message of the score modification
    """
    try:
        current_grade = st.session_state.get("current_grade")
        current_feedback = st.session_state.get("current_feedback", "")
        student_name = st.session_state.get("selected_student_name", "Unknown Student")
        
        if not input_str:
            return (
                "Please specify the new score:\n"
                "- Format: 'modify grade score: XX' where XX is a number between 0 and 100"
            )
            
        if "score:" in input_str.lower():
            try:
                new_score = float(input_str.lower().split("score:")[1].strip())
                if 0 <= new_score <= 100:
                    st.session_state.current_grade = new_score
                    
                    # Update the score in the feedback if it exists
                    if current_feedback:
                        feedback_lines = current_feedback.split('\n')
                        if len(feedback_lines) > 0:
                            if "Score:" in feedback_lines[0] or "Overall Score:" in feedback_lines[0]:
                                feedback_lines[0] = f"Overall Score: {new_score}/100"
                            else:
                                feedback_lines.insert(0, f"Overall Score: {new_score}/100")
                            st.session_state.current_feedback = '\n'.join(feedback_lines)
                    else:
                        st.session_state.current_feedback = f"Overall Score: {new_score}/100"
                    
                    # Show both score update and current feedback
                    response = [
                        f"Score updated to {new_score}/100 for {student_name}",
                        "\nCurrent feedback:",
                        st.session_state.current_feedback,
                        "\nOptions:",
                        "- To modify feedback: 'feedback: your new feedback'",
                        "- To submit to Canvas: 'submit grade to canvas'"
                    ]
                    return "\n".join(response)
                else:
                    return "Score must be between 0 and 100"
            except:
                return "Invalid score format. Please use 'modify grade score: XX' where XX is a number between 0 and 100"
        else:
            return "Please use 'modify grade score: XX' where XX is a number between 0 and 100"
            
    except Exception as e:
        return f"Error modifying grade: {str(e)}"

@tool
def modify_feedback_tool(input_str: str = "") -> str:
    """Modify the feedback for the last graded submission.
    
    Args:
        input_str: The new feedback text
        
    Returns:
        str: Confirmation message of the feedback modification
    """
    try:
        current_grade = st.session_state.get("current_grade")
        student_name = st.session_state.get("selected_student_name", "Unknown Student")
        
        if not input_str:
            return "Please provide the new feedback text."
        
        # Create feedback with score if available
        if current_grade is not None:
            new_feedback = f"Overall Score: {current_grade}/100\n\n{input_str}"
        else:
            new_feedback = input_str
        
        # Update the feedback
        st.session_state.current_feedback = new_feedback
        
        # Show the updated feedback
        response = [
            f"Feedback updated for {student_name}:",
            new_feedback,
            "\nOptions:",
            "- To modify score: 'modify grade score: XX'",
            "- To submit to Canvas: 'submit grade to canvas'"
        ]
        return "\n".join(response)
        
    except Exception as e:
        return f"Error modifying feedback: {str(e)}"

@tool
def show_feedback_tool(input_str: str = "") -> str:
    """Show the current feedback and grade for the submission.
    
    Args:
        input_str: Not used
        
    Returns:
        str: Current feedback and grade
    """
    try:
        current_grade = st.session_state.get("current_grade")
        current_feedback = st.session_state.get("current_feedback")
        student_name = st.session_state.get("selected_student_name", "Unknown Student")
        
        if current_grade is None and not current_feedback:
            return "No feedback available. Please grade a submission first."
            
        response = [
            f"Current grade and feedback for {student_name}:",
            f"\nGrade: {current_grade}/100" if current_grade is not None else "",
            "\nFeedback:",
            current_feedback if current_feedback else "No feedback provided",
            "\nOptions:",
            "- To modify score: 'modify grade score: XX'",
            "- To modify feedback: 'feedback: your new feedback'",
            "- To submit to Canvas: 'submit grade to canvas'"
        ]
        
        return "\n".join(filter(None, response))
        
    except Exception as e:
        return f"Error showing feedback: {str(e)}"

@tool
def submit_to_canvas_tool(input_str: str = "") -> str:
    """Submit the current grade and feedback to Canvas.
    
    Args:
        input_str: Optional string (not used)
        
    Returns:
        str: Confirmation message of the submission to Canvas
    """
    try:
        course_id = st.session_state.get("course_id")
        assignment_id = st.session_state.get("assignment_id")
        student_id = st.session_state.get("student_id")
        current_grade = st.session_state.get("current_grade")
        current_feedback = st.session_state.get("current_feedback")
        
        if not all([course_id, assignment_id, student_id]):
            return "Missing required information. Please ensure a submission is selected first."
            
        if current_grade is None:
            return "No grade to submit. Please grade the submission first."
            
        # Print debug info
        print(f"Submitting to Canvas - Grade: {current_grade}, Feedback: {current_feedback}")
        
        result = submit_grade_and_feedback(
            user_id=student_id,
            course_id=course_id,
            assignment_id=assignment_id,
            grade=current_grade,
            feedback=current_feedback
        )
        
        return result
        
    except Exception as e:
        return f"Error submitting to Canvas: {str(e)}"