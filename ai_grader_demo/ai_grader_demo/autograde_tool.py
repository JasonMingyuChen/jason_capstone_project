from langchain.tools import tool
from api.canvas_api import get_assignment_rubric, get_submissions, submit_grade_and_feedback
from utils.rubric_parser import parse_rubric
from langchain_openai import ChatOpenAI
import streamlit as st
import re
import json

llm = ChatOpenAI(model="gpt-4", temperature=0.3)

@tool
def auto_grade_and_submit_tool(input_str: str) -> str:
    """
    Automatically fetches, grades, and submits feedback for a student's assignment.
    Input format: "course_id,assignment_id,student_id"
    """
    try:
        course_id, assignment_id, student_id = map(str.strip, input_str.split(","))

        # Fetch submission
        submissions = get_submissions(course_id, assignment_id)
        submission = next((s for s in submissions if str(s["user_id"]) == student_id), None)
        if not submission:
            return f" No submission found for student {student_id}."

        name = submission.get("user", {}).get("name", "Unknown")
        body = submission.get("body", "")
        if not body:
            return f" Submission is empty."

        # Fetch rubric
        rubric_raw = get_assignment_rubric(course_id, assignment_id)
        if not rubric_raw:
            return f" No rubric found for this assignment."
        rubric = parse_rubric(rubric_raw)
        if not rubric:
            return f" Failed to parse rubric."

        # Grade the submission
        feedback_sections = []
        total_score = 0.0
        max_score = 0.0

        for crit in rubric:
            prompt = (
                f"Evaluate the following student submission according to this criterion:\n\n"
                f"Submission:\n{body}\n\n"
                f"Criterion: {crit['title']} ({crit['points']} pts)\n"
                f"Description: {crit['description']}\n\n"
                "Return score (0 to full points) and 1-sentence feedback."
            )
            result = llm.invoke(prompt).content.strip()
            feedback_sections.append(f"**{crit['title']} ({crit['points']} pts)**:\n{result}")

            match = re.search(r"(\d+(\.\d+)?)[\/\s]", result)
            try:
                score = float(match.group(1)) if match else 0
            except:
                score = 0

            total_score += score
            max_score += crit["points"]

        feedback_text = "\n\n".join(feedback_sections)
        summary = (
            f"The grading is complete. The student, {name}, has received the following feedback:\n\n"
            f"{feedback_text}\n\n"
            f"Total score: {total_score:.2f}/{max_score:.0f}"
        )

        # Submit to Canvas
        result = submit_grade_and_feedback(
            user_id=student_id,
            course_id=course_id,
            assignment_id=assignment_id,
            grade=str(round(total_score, 2)),
            feedback=feedback_text
        )

        return f" Grading submitted for {name} (ID: {student_id}).\n\n{summary}\n\nCanvas response: {result}"

    except Exception as e:
        return f" Auto-grade failed: {str(e)}"
