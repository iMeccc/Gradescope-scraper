import requests
import time
from bs4 import BeautifulSoup
from bs4.element import Tag


# set basic variables
TARGET_URL = "https://www.gradescope.com" # consider receive custom urls
LOGIN_URL = f"{TARGET_URL}/login"

def request_session(session: requests.Session, method: str, url: str, retries : int = 2, timeout: int = 10, backoff: int = 1, **kwargs):
    # A small wrapper around session.get/post that adds timeout and simple retries.
    # Returns the Response on success, or None on persistent failure.

    last_exc = None # store last exception 
    # for every attempts, check its accessibility and raise error if occurs
    for attempt in range(1,retries+1):
        try:
            if method.lower() == 'get':
                resp = session.get(url, timeout = timeout, **kwargs)
            elif method.lower() == 'post':
                resp = session.post(url, timeout = timeout, **kwargs)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            last_exc = e
            print(f'Request error ({method.upper()}){url!r} attempt {attempt}/{retries}: {e}')
            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2
    if last_exc is not None: 
        print(f'Failed to fetch {url!r} after {retries} attempts. Last error: {last_exc!r}')
    else:
        print(f'Failed to fetch {url!r} after {retries} attempts.') 
    return None

def log_into_gradescope(session, email, password):
    # deal with the login process and return a session which holds the login status
    
    # 1. visit the login page
    print('Accessing login page')
    get_response = request_session(session, 'get', TARGET_URL)
    if get_response is None:
        print('Login access failed, please check your configuration')
        return None
    
    # 2. analyse HTML and find 'authenticity_token' in the firmest way
    soup = BeautifulSoup(get_response.text, 'html.parser')
    token_element = soup.find('meta', {'name': 'csrf-token'})
    # make sure the element is a 'Tag' to avoid TypeError
    if not isinstance(token_element, Tag):
        print("No 'csrf-token' meta Tag found in page, login failed.")
        return None
    authenticity_token = token_element.get('content')
    if not authenticity_token:
        print("Found 'csrf-token' Tag, however no 'content' property inside, login failed.")
        return None
    
    print('Successfully acquired authenticity_token.')

    # 3. construct the POST request payload
    payload = {
        "session[email]": email,
        "session[password]": password,
        "authenticity_token": authenticity_token,
        "commit": "Log In"
    } 

    # 4. send POST request and accomplish login
    print('Submitting login payload...')
    post_response = request_session(session, 'post', TARGET_URL, data = payload)
    if post_response is None:
        print('Login payload submission failed, please check website updates.')
        return None
    
    # 5. verify login status
    successful_urls = [f"{TARGET_URL}/account"]
    if post_response.url in successful_urls:
        print('Login successfully!')
        return session
    else:
        print('Login failed, please check your email/password.')
        print(f"Page remain at {post_response.url}")
        return None
    
def get_courses(session):
    # fetch all courses from Gradescope dashboard
    courses_url =  "https://www.gradescope.com/account"
    response = request_session(session, 'get', courses_url)
    if response is None:
        print('Error fetching courses.')
        return []
    soup = BeautifulSoup(response.text, 'html.parser')
    courses = []
    # Find all course links on the page. Try multiple selectors for robustness.
    course_tags = soup.select(".courseList--coursesForTerm a.courseBox[href^='/courses/']")
    if not course_tags:
        course_tags = soup.select('a.courseBox')
    for tag in course_tags:
        if isinstance(tag, Tag):
            course_name_tag = tag.find('div', class_='courseBox--name')
            course_term_tag = tag.find('div', class_='courseBox--shortTerm' )

            name: str | None = None
            term: str | None = None
            if isinstance(course_name_tag, Tag):
                name = course_name_tag.get_text(strip = True)
            if isinstance(course_term_tag, Tag):
                term = course_term_tag.get_text(strip = True)
            if not name:
                # Fallback to anchor text if structured name not found
                name = tag.get_text(strip = True)

            href = tag.get('href')
            # If term not found inside the anchor, try to lookup from the surrounding section
            if href and isinstance(href, str):
                if not term:
                    parent_section = tag.find_parent('div', class_='courseList')
                    if isinstance(parent_section, Tag):
                        term_tag = parent_section.find('div', class_='courseList--term')
                        if isinstance(term_tag, Tag):
                            term = term_tag.get_text(strip = True)
                
                full_name = f"{name} - {term}" if term else name
                courses.append({"name": full_name, "url":f"https://www.gradescope.com{href}"})

    return courses



if __name__ == '__main__':
    session = requests.Session()
    # set common request headers
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Referer": "https://www.gradescope.com/login"
    })

