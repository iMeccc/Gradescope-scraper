import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import os

# --- 常量定义 ---
# Gradescope 的主页和登录相关的 URL
BASE_URL = "https://www.gradescope.com"
LOGIN_URL = f"{BASE_URL}/login"

# --- 核心功能 ---

def login_to_gradescope(session, email, password):
    """
    处理登录逻辑，返回一个保持登录状态的 session 对象。
    """
    # 1. GET 请求：访问登录页面
    print("正在访问登录页面...")
    try:
        get_response = session.get(LOGIN_URL)
        get_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"访问登录页面失败: {e}")
        return None

    # 2. 解析 HTML，并以最健壮的方式找到 authenticity_token
    soup = BeautifulSoup(get_response.text, "html.parser")
    token_element = soup.find("meta", {"name": "csrf-token"})

    # 明确检查找到的元素是否是一个“标签”，这是消除类型错误的根本方法
    if not isinstance(token_element, Tag):
        print("无法在页面上找到 'csrf-token' meta 标签，登录失败。")
        return None

    authenticity_token = token_element.get("content")
    if not authenticity_token:
        print("找到了 'csrf-token' 标签，但其中没有 'content' 属性，登录失败。")
        return None
    
    print("成功获取 authenticity_token。")

    # 3. 构造 POST 请求的 payload
    payload = {
        "session[email]": email,
        "session[password]": password,
        "authenticity_token": authenticity_token,
        "commit": "Log In"
    }

    # 4. 发送 POST 请求，完成登录
    print("正在提交登录信息...")
    try:
        post_response = session.post(LOGIN_URL, data=payload)
        post_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"提交登录信息失败: {e}")
        return None

    # 5. 验证登录是否成功
    # 根据我们的实验，登录成功后可能跳转到 /courses 或 /account
    successful_urls = [f"{BASE_URL}/courses", f"{BASE_URL}/account"]
    if post_response.url in successful_urls:
        print("登录成功！")
        return session
    else:
        print("登录失败，请检查账号或密码。")
        print(f"提示：登录后页面停留在 {post_response.url} (预期为 {successful_urls[0]} 或 {successful_urls[1]})")
        return None


def get_courses(session: requests.Session) -> list[dict[str, str]]:
    """
    Fetches all courses from the Gradescope dashboard.

    Args:
        session: The logged-in requests session.

    Returns:
        A list of dictionaries, where each dictionary represents a course
        and contains 'name' and 'url'.
    """
    courses_url = "https://www.gradescope.com/account"
    try:
        response = session.get(courses_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching courses page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    courses = []
    # Find all course links on the page. Try multiple selectors for robustness.
    course_tags = soup.select(".courseList--coursesForTerm a.courseBox[href^='/courses/']")
    if not course_tags:
        course_tags = soup.select("a.courseBox")
    print(f"DEBUG: Found {len(course_tags)} potential course anchors")
    for tag in course_tags:
        if isinstance(tag, Tag):
            course_name_tag = tag.find("div", class_="courseBox--name")
            course_term_tag = tag.find("div", class_="courseBox--shortTerm")
            
            name: str | None = None
            term: str | None = None
            if isinstance(course_name_tag, Tag):
                name = course_name_tag.get_text(strip=True)
            if isinstance(course_term_tag, Tag):
                term = course_term_tag.get_text(strip=True)

            if not name:
                # Fallback to anchor text if structured name not found
                name = tag.get_text(strip=True)

            href = tag.get("href")
            if href and isinstance(href, str):
                # If term not found inside the anchor, try to lookup from the surrounding section
                if not term:
                    parent_section = tag.find_parent("div", class_="courseList")
                    if isinstance(parent_section, Tag):
                        term_tag = parent_section.find("div", class_="courseList--term")
                        if isinstance(term_tag, Tag):
                            term = term_tag.get_text(strip=True)

                full_name = f"{name} - {term}" if term else name
                courses.append({"name": full_name, "url": f"https://www.gradescope.com{href}"})

    return courses


def get_assignments(session: requests.Session, course_url: str) -> list[dict[str, str]]:
    """
    Fetches the list of unsubmitted assignments for a specific course.

    Args:
        session: The logged-in requests session.
        course_url: The URL of the course to scrape.

    Returns:
        A list of dictionaries, where each dictionary represents an
        unsubmitted assignment and contains its name, link, status, and due date.
    """
    print(f"Fetching assignments from {course_url}...")
    try:
        # Use the provided course_url
        response = session.get(course_url)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching assignments page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    unsubmitted_assignments = []

    # 1. 安全地定位到表格主体
    table_body = soup.select_one("table#assignments-student-table tbody")
    if not isinstance(table_body, Tag):
        print("错误：在页面上未能找到作业表格主体 (tbody)。")
        return []

    # 2. 安全地遍历每一行
    # 通过 list() 转换，让类型检查器明确知道这是一个列表
    assignment_rows = list(table_body.find_all("tr", recursive=False))
    print(f"在表格中找到了 {len(assignment_rows)} 个作业条目，正在筛选...")

    for row in assignment_rows:
        # 确保 row 是一个 Tag 对象
        if not isinstance(row, Tag):
            continue

                # --- 全新的、更健壮的信息提取与筛选逻辑 ---

        # 1. 提取名称和链接 (这部分逻辑是正确的，保持不变)
        name, link = None, None
        name_th = row.find("th", scope="row")
        if isinstance(name_th, Tag):
            name = name_th.get_text(strip=True)
            link_a = name_th.find("a")
            if isinstance(link_a, Tag):
                href = link_a.get("href")
                if isinstance(href, str):
                    link = BASE_URL + href
        
        if not name or not link:
            continue

        # 2. 重新设计的状态和日期提取
        is_completed = False
        status_text = ""
        due_date = ""
        all_tds = row.find_all("td")

        # 状态单元格是第一个 <td>
        if len(all_tds) > 0:
            status_td = all_tds[0]
            if isinstance(status_td, Tag):
                status_text = status_td.get_text(strip=True)
                raw_classes = status_td.get("class")
                if isinstance(raw_classes, list):
                    status_classes = [str(cls) for cls in raw_classes]
                elif isinstance(raw_classes, str):
                    status_classes = [raw_classes]
                else:
                    status_classes = []

                # --- 智能筛选逻辑 ---
                # 条件1: 状态是 "Submitted"
                if 'submissionStatus-complete' in status_classes:
                    is_completed = True
                # 条件2: 状态是已评分 (文本中包含分数)
                elif '/' in status_text and any(char.isdigit() for char in status_text):
                    is_completed = True
        
        # 截止日期单元格是倒数第二个 <td>
        if len(all_tds) >= 2:
            due_date_td = all_tds[-2]
            if isinstance(due_date_td, Tag):
                due_date = due_date_td.get_text(strip=True)

        # 3. 根据筛选结果决定是否添加
        if not is_completed:
            unsubmitted_assignments.append({
                "name": name,
                "link": link,
                "status": status_text,
                "due_date": due_date
            })

    return unsubmitted_assignments

def send_notification(assignments: list[dict[str, str]]) -> None:
    pass


# --- 主程序入口 ---

if __name__ == "__main__":
    session = requests.Session()
    # 设置常见浏览器请求头，避免因默认 UA 被服务器屏蔽或返回简化页面
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7",
        "Referer": "https://www.gradescope.com/login"
    })

    # Load email and password from environment variables
    email = os.getenv("GRADESCOPE_EMAIL")
    password = os.getenv("GRADESCOPE_PASSWORD")

    if not email or not password:
        print("Error: GRADESCOPE_EMAIL and GRADESCOPE_PASSWORD environment variables must be set.")
    else:
        logged_in_session = login_to_gradescope(session, email, password)

        if logged_in_session:
            print("Login successful.")
            courses = get_courses(logged_in_session)
            if not courses:
                print("No courses found.")
            else:
                print(f"Found {len(courses)} courses.")
                all_unsubmitted_assignments = []
                for course in courses:
                    print(f"\nChecking course: {course['name']}")
                    unsubmitted_assignments = get_assignments(logged_in_session, course['url'])
                    if unsubmitted_assignments:
                        for assignment in unsubmitted_assignments:
                            assignment['course_name'] = course['name'] # Add course name to assignment info
                        all_unsubmitted_assignments.extend(unsubmitted_assignments)

                if not all_unsubmitted_assignments:
                    print("\nNo unsubmitted assignments found in any course. Great job!")
                else:
                    print("\n--- Summary of Unsubmitted Assignments ---")
                    for assignment in all_unsubmitted_assignments:
                        print(f"  Course: {assignment['course_name']}")
                        print(f"  Assignment: {assignment['name']}")
                        print(f"  Status: {assignment['status']}")
                        print(f"  Due Date: {assignment['due_date']}")
                        print("-" * 20)
        else:
            print("Login failed.")