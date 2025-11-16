import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import os
import smtplib
from email.message import EmailMessage
import time

# --- 常量定义 ---
# Gradescope 的主页和登录相关的 URL
BASE_URL = "https://www.gradescope.com"
LOGIN_URL = f"{BASE_URL}/login"

# --- 核心功能 ---


def safe_request(session: requests.Session, method: str, url: str, retries: int = 2, timeout: int = 10, backoff: int = 1, **kwargs):
    """
    A small wrapper around session.get/post that adds timeout and simple retries.

    Returns the Response on success, or None on persistent failure.
    """
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            if method.lower() == "get":
                resp = session.get(url, timeout=timeout, **kwargs)
            else:
                resp = session.post(url, timeout=timeout, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            last_exc = e
            print(f"Request error ({method.upper()}) {url!r} attempt {attempt}/{retries}: {e}")
            if attempt < retries:
                time.sleep(backoff)
                backoff *= 2

    print(f"Failed to fetch {url!r} after {retries} attempts.")
    return None


def login_to_gradescope(session, email, password):
    """
    处理登录逻辑，返回一个保持登录状态的 session 对象。
    """
    # 1. GET 请求：访问登录页面
    print("正在访问登录页面...")
    get_response = safe_request(session, "get", LOGIN_URL)
    if get_response is None:
        print("访问登录页面失败: 多次尝试均未成功。")
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
    post_response = safe_request(session, "post", LOGIN_URL, data=payload)
    if post_response is None:
        print("提交登录信息失败: 多次尝试均未成功。")
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
    response = safe_request(session, "get", courses_url)
    if response is None:
        print("Error fetching courses page: 多次尝试均未成功。")
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
    # Use safe_request with retries and timeout
    response = safe_request(session, "get", course_url)
    if response is None:
        print(f"Error fetching assignments page for {course_url}: 多次尝试均未成功。")
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
    host = os.getenv("SMTP_HOST")
    port_str = os.getenv("SMTP_PORT", "465")
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    to_addr = os.getenv("SMTP_TO")
    from_addr = os.getenv("SMTP_FROM") or user
    debug = os.getenv("SMTP_DEBUG") == "1"

    try:
        port = int(port_str)
    except ValueError:
        print(f"Error: SMTP_PORT must be an integer, got {port_str!r}")
        return

    # 基础校验
    if not all([host, port, user, password, to_addr, from_addr]):
        print("Error: Missing SMTP environment variables (SMTP_HOST/PORT/USER/PASSWORD/TO).")
        return
    if not assignments:
        print("No assignments to notify; skipping email.")
        return

    # 组装正文
    lines = [f"共发现未提交作业 {len(assignments)} 项："]
    for i, a in enumerate(assignments, start=1):
        course = a.get("course_name", "(未识别课程)")
        name = a.get("name", "(未识别作业)")
        status = a.get("status", "")
        due = a.get("due_date", "")
        link = a.get("link", "")
        lines.append(f"{i}. 课程: {course}")
        lines.append(f"   作业: {name}")
        if status:
            lines.append(f"   状态: {status}")
        if due:
            lines.append(f"   截止: {due}")
        if link:
            lines.append(f"   链接: {link}")
        lines.append("-" * 20)
    body = "\n".join(lines)

    subject = f"[Gradescope] 未提交作业 {len(assignments)} 项"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg.set_content(body)

    # 建立连接并发送，区分 SSL(465) 与 STARTTLS(587)
    if port == 465:
        server = None
        try:
            server = smtplib.SMTP_SSL(host, port, timeout=15)
            if debug:
                server.set_debuglevel(1)
                print(f"SMTP DEBUG: using SSL connect to {host}:{port}")
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
            print("Notification email sent.")
        except Exception as e:
            print("Error during SMTP SSL send:", repr(e))
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
                        pass
    else:
        server = None
        try:
            server = smtplib.SMTP(host, port, timeout=15)
            if debug:
                server.set_debuglevel(1)
                print(f"SMTP DEBUG: using STARTTLS connect to {host}:{port}")
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(user, password)
            server.send_message(msg)
            print("Notification email sent.")
        except Exception as e:
            print("Error during SMTP STARTTLS send:", repr(e))
        finally:
            if server:
                try:
                    server.quit()
                except Exception:
                    try:
                        server.close()
                    except Exception:
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

                # 如果需要强制测试邮件（例如当前没有未提交作业），
                # 可通过设置环境变量 `SMTP_FORCE_TEST=1` 来注入一条测试作业。
                if not all_unsubmitted_assignments and os.getenv("SMTP_FORCE_TEST") == "1":
                    print("INFO: SMTP_FORCE_TEST=1 detected — injecting test assignment for email test.")
                    all_unsubmitted_assignments = [
                        {
                            "course_name": "测试课程",
                            "name": "测试作业",
                            "status": "No Submission",
                            "due_date": "N/A",
                            "link": "https://www.gradescope.com"
                        }
                    ]

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

                    # 打印全部条目后只发送一次邮件通知（避免重复发送）
                    send_notification(all_unsubmitted_assignments)
        else:
            print("Login failed.")