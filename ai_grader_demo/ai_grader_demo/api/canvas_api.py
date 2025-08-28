import requests
from .config import API_URL, ACCESS_TOKEN


def get_submissions(course_id, assignment_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    url = f"{API_URL}/courses/{course_id}/assignments/{assignment_id}/submissions"
    
    try:
        response = requests.get(
            url,
            headers=headers,
            params={"per_page": 100, "include[]": ["submission_comments", "user"]}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching submissions: {str(e)}")
        return []


def get_assignment_rubric(course_id, assignment_id):
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    url = f"{API_URL}/courses/{course_id}/assignments/{assignment_id}"
    
    try:
        response = requests.get(url, headers=headers, params={"include[]": "rubric"})
        response.raise_for_status()
        data = response.json()
        return data.get("rubric", [])
    except Exception as e:
        print(f"Error fetching rubric: {str(e)}")
        return []


def submit_grade_and_feedback(user_id, course_id, assignment_id, grade, feedback):
    url = f"{API_URL}/courses/{course_id}/assignments/{assignment_id}/submissions/{user_id}"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    
    data = {
        "comment[text_comment]": feedback,
        "submission[posted_grade]": str(grade)
    }

    try:
        response = requests.put(url, headers=headers, data=data)
        if response.status_code == 200:
            return f"✅ Submitted feedback for user {user_id}."
        else:
            return f"❌ Canvas responded with {response.status_code}: {response.text}"
    except Exception as e:
        return f"❌ Error submitting feedback: {str(e)}"
