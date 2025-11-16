import os
import requests
from bs4 import BeautifulSoup, Tag

def login_to_gradescope(session: requests.Session, email: str, password: str) -> requests.Session | None:
    """
    Logs into Gradescope and returns the session object.

    Args:
        session: A requests.Session object.
        email: The user's email address.
        password: The user's password.

    Returns:
        The logged-in requests.Session object if successful, otherwise None.
    """
    login_url = "https://www.gradescope.com/login"
    print("Visiting login page...")
    try:
        response = session.get(login_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error visiting login page: {e}")
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    token_tag = soup.find("meta", {"name": "csrf-token"})

    if not isinstance(token_tag, Tag):
        print("Error: Could not find authenticity_token on login page.")
        return None

    authenticity_token = token_tag.get("content")
    if not authenticity_token:
        print("Error: authenticity_token content is empty.")
        return None
    
    print("Successfully found authenticity_token.")

    payload = {
        "session[email]": email,
        "session[password]": password,
        "authenticity_token": authenticity_token,
        "commit": "Log In",
    }

    print("Submitting login information...")
    try:
        post_response = session.post(login_url, data=payload)
        post_response.raise_for_status()

        # Successful login can redirect to /courses or /account
        if post_response.url.endswith("/courses") or post_response.url.endswith("/account"):
            return session
        else:
            print("Login failed. Final URL:", post_response.url)
            # Consider saving post_response.text to a file for debugging if needed
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error during login POST request: {e}")
        return None


def get_assignments(session: requests.Session) -> list[dict[str, str]]:
    """
    Fetches the list of unsubmitted assignments.

    Args:
        session: The logged-in requests session.

    Returns:
        A list of dictionaries, where each dictionary represents an
        unsubmitted assignment and contains its name, link, status, and due date.
    """
    # This URL is for a specific course.
    # You will need to change this to your course's URL.
    course_url = "https://www.gradescope.com/courses/1132878"
    print(f"Fetching assignments from {course_url}...")
    try:
        response = session.get(course_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching assignments page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table", {"id": "assignments-student-table"})
    if not isinstance(table, Tag):
        print("Could not find the assignments table.")
        return []

    tbody = table.find("tbody")
    if not isinstance(tbody, Tag):
        print("Could not find the assignments table body.")
        return []

    assignments_rows = tbody.find_all("tr")
    unsubmitted_assignments = []

    for row in assignments_rows:
        if isinstance(row, Tag):
            # Check if the assignment is complete
            status_cell = row.find("td", class_="submissionStatus")
            is_complete = False
            if isinstance(status_cell, Tag):
                status_classes = status_cell.get("class")
                if isinstance(status_classes, list):
                    if "submissionStatus-complete" in status_classes:
                        is_complete = True
                elif isinstance(status_classes, str):
                    if "submissionStatus-complete" in status_classes.split():
                        is_complete = True
                if not is_complete and "/" in status_cell.get_text():
                    is_complete = True
            
            # If not complete, extract its details
            if not is_complete:
                name_cell = row.find("th")
                link_tag = name_cell.find("a") if isinstance(name_cell, Tag) else None
                
                due_date_cell = row.find("td", class_="submissionTime")

                assignment_info = {}

                if isinstance(name_cell, Tag):
                    assignment_info["name"] = name_cell.text.strip()
                else:
                    assignment_info["name"] = "Name not found"

                if isinstance(link_tag, Tag):
                    assignment_info["link"] = f"https://www.gradescope.com{link_tag.get('href')}"
                else:
                    assignment_info["link"] = "Link not found"
                
                if isinstance(status_cell, Tag):
                    assignment_info["status"] = status_cell.text.strip()
                else:
                    assignment_info["status"] = "Status not found"

                if isinstance(due_date_cell, Tag):
                    assignment_info["due_date"] = due_date_cell.text.strip()
                else:
                    assignment_info["due_date"] = "Due date not found"
                
                unsubmitted_assignments.append(assignment_info)

    return unsubmitted_assignments


def send_notification(assignments: list[dict[str, str]]) -> None:
    """

    (This function is a placeholder for sending email notifications.)
    """
    pass


if __name__ == "__main__":
    session = requests.Session()

    # Load email and password from environment variables
    email = os.getenv("GRADESCOPE_EMAIL")
    password = os.getenv("GRADESCOPE_PASSWORD")

    if not email or not password:
        print("Error: GRADESCOPE_EMAIL and GRADESCOPE_PASSWORD environment variables must be set.")
    else:
        logged_in_session = login_to_gradescope(session, email, password)

        if logged_in_session:
            print("Login successful. Fetching assignments...")
            unsubmitted_assignments = get_assignments(logged_in_session)
            if not unsubmitted_assignments:
                print("No unsubmitted assignments found. Great job!")
            else:
                print("Unsubmitted assignments found:")
                for assignment in unsubmitted_assignments:
                    print(
                        f"  - Name: {assignment['name']}, "
                        f"Status: {assignment['status']}, "
                        f"Due: {assignment['due_date']}"
                    )
        else:
            print("Login failed.")
