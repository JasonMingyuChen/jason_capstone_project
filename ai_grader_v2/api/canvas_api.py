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
    if not course_id or not assignment_id:
        print("Error: Missing course_id or assignment_id")
        return []
        
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    url = f"{API_URL}/courses/{course_id}/assignments/{assignment_id}"
    print(f"Making API request to: {url}")
    
    try:
        response = requests.get(url, headers=headers, params={"include[]": "rubric"})
        print(f"API response status: {response.status_code}")
        
        if response.status_code == 401:
            error_data = response.json()
            if "errors" in error_data and error_data["errors"]:
                error_msg = error_data["errors"][0].get("message", "Unknown error")
                print(f"Authentication error: {error_msg}")
                if "expired" in error_msg.lower():
                    return "Your Canvas API token has expired. Please generate a new token in Canvas settings."
            return "Failed to authenticate with Canvas. Please check your API token."
            
        response.raise_for_status()
        data = response.json()
        rubric = data.get("rubric", [])
        print(f"Got rubric data: {bool(rubric)}")
        return rubric
    except requests.exceptions.RequestException as e:
        print(f"Error in get_assignment_rubric: {str(e)}")
        print(f"Response content: {getattr(response, 'text', 'No response content')}")
        return []
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
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
