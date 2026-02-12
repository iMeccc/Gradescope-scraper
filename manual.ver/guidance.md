好的，非常棒的学习方法！这个 AI 生成的代码质量相当不错，包含了很多健壮性和安全性的最佳实践。让我们把它像解剖课一样，一层层地剥开，看看它的“骨骼”、“肌肉”和“神经系统”。

我将按照代码的执行逻辑顺序，并结合功能模块来进行分段解析。

---

### **模块一：依赖导入与常量定义**

```python
import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
import os
import smtplib
from email.message import EmailMessage
import time

# --- 常量定义 ---
BASE_URL = "https://www.gradescope.com"
LOGIN_URL = f"{BASE_URL}/login"
```

*   **功能 (Function):**
    这是程序的准备阶段。它告诉 Python：“接下来我要用到这些工具箱，请帮我准备好”。同时，它定义了两个不会改变的全局变量（常量），用于表示目标网站的基础网址，方便后续引用和修改。

*   **实现原理 (Principle):**
    *   `import` 语句是 Python 的核心机制，用于加载外部库或内置模块，让我们可以使用别人已经写好的强大功能，而无需自己“造轮子”。
    *   `from bs4.element import Tag`: 这是一个特别的导入。`BeautifulSoup` 在解析时会创建不同类型的对象，`Tag` 代表一个 HTML 标签（如 `<div>`, `<a>`）。通过显式导入它，我们可以在代码后面进行精确的类型检查，这是提升代码健壮性的高级技巧。
    *   **常量定义**: 将固定的网址定义成常量，如果未来网站 URL 结构变化，我们只需要修改这一处，而不用在代码的各个角落里去寻找和替换，这遵循了 **DRY (Don't Repeat Yourself)** 原则。

*   **注意细节 (Details):**
    *   `requests`: 用于发送 HTTP 请求，是爬虫的“手”，负责与网站服务器打交道。
    *   `BeautifulSoup`: 用于解析 HTML/XML，是爬虫的“眼睛”，负责从杂乱的网页源码中看懂结构。
    *   `os`: 用于与操作系统交互，这里主要是为了读取环境变量 (`os.getenv`)，实现配置与代码分离。
    *   `smtplib` 和 `email.message`: Python 内置的邮件双雄，前者负责发送，后者负责构建邮件本身。

---

### **模块二：健壮的网络请求 (`safe_request` 函数)**

```python
def safe_request(session: requests.Session, method: str, url: str, retries: int = 2, timeout: int = 10, backoff: int = 1, **kwargs):
    # ... (函数体)
```

*   **功能 (Function):**
    这个函数不是一个普通的请求发送器，而是一个**“永不言弃”的加强版请求发送器**。它封装了 `requests` 的 `get` 和 `post` 方法，并增加了**超时、自动重试和指数退避**功能。

*   **实现原理 (Principle):**
    *   **超时 (`timeout`)**: 防止因目标网站响应过慢而导致程序无限期卡死。它告诉 `requests`：“如果 10 秒内对方没反应，就算作失败”。
    *   **自动重试 (`retries`)**: 网络偶尔会抖动，导致请求失败。该函数通过一个 `for` 循环，在失败后自动尝试多次，大大提高了爬取成功率。
    *   **指数退避 (`backoff`)**: 这是比简单重试更“聪明”的策略。它在每次重试失败后，会把等待时间加倍 (`backoff *= 2`)。这样做可以避免因过于频繁地请求而被服务器误判为攻击，是一种更友好的重试方式。
    *   **异常处理 (`try...except`)**: 使用 `try...except` 结构捕获所有可能的 `requests` 网络异常，确保程序不会因为一次网络问题而崩溃。

*   **注意细节 (Details):**
    *   `session: requests.Session`: 类型注解，表明这个函数期望接收一个 `Session` 对象。`Session` 对象可以在多次请求之间保持 cookies，这对于需要登录的爬虫至关重要。
    *   `resp.raise_for_status()`: 这是一个非常有用的 `requests` 方法。如果 HTTP 状态码是 4xx（客户端错误）或 5xx（服务器错误），它会自动抛出一个异常，让我们的 `try...except` 逻辑能捕获到非 200 的成功状态。
    *   `**kwargs`: 这个参数允许你向 `safe_request` 传递任意其他 `requests` 支持的参数（比如 `data`, `headers`），增加了函数的灵活性。

---

### **模块三：登录逻辑 (`login_to_gradescope` 函数)**

```python
def login_to_gradescope(session, email, password):
    # ... (函数体)
```

*   **功能 (Function):**
    模拟用户在浏览器上输入账号、密码并点击“登录”按钮的全过程。这是与需要登录的网站交互的**第一道门槛**。

*   **实现原理 (Principle):**
    这是一个经典的“两步走”登录模式：
    1.  **GET 请求**: 首先像普通访客一样访问登录页面。这么做的**唯一目的**是为了从返回的 HTML 中获取一个隐藏的、动态生成的 `authenticity_token` (也叫 CSRF token)。
    2.  **POST 请求**: 将我们的用户名、密码，**连同上一步获取的 `authenticity_token`**，一起打包成一个 `payload`（表单数据），然后用 `POST` 方法发送给登录接口。服务器会验证这个 token，以确保请求真的是从它的登录页面发起的，而不是伪造的。

*   **注意细节 (Details):**
    *   `soup.find("meta", {"name": "csrf-token"})`: AI 精确地知道这个 token 藏在一个 `<meta>` 标签里。这是通过分析真实网页的 HTML 结构得出的结论，是你复现时需要用**浏览器开发者工具(F12)** 去做的“侦察工作”。
    *   `isinstance(token_element, Tag)`: **这是代码中最值得学习的细节之一！** 在爬虫中，`find` 或 `select` 找不到元素时会返回 `None`。如果直接在 `None` 上调用 `.get("content")` 就会导致程序崩溃 (`AttributeError`)。这里通过类型检查，确保了只有在**真正找到**一个标签时，才去尝试获取它的属性，这叫**防御性编程**，极大地增强了代码的稳定性。
    *   `post_response.url in successful_urls`: 登录后，网站服务器会返回一个“重定向”指令，让浏览器跳转到课程主页。代码通过检查最终停留的 URL 是否为预期的课程页，来判断登录是否真的成功。

---

### **模块四：数据提取（`get_courses` 和 `get_assignments`）**

```python
def get_courses(session: requests.Session) -> list[dict[str, str]]:
    # ... (函数体)

def get_assignments(session: requests.Session, course_url: str) -> list[dict[str, str]]:
    # ... (函数体)
```

*   **功能 (Function):**
    这是爬虫的**核心价值**所在。`get_courses` 负责在主页上抓取所有课程的名称和链接。`get_assignments` 则进入每一个课程页面，抓取其中所有**未提交**作业的详细信息。

*   **实现原理 (Principle):**
    *   **HTML 定位**: 两者都使用了 `BeautifulSoup` 的核心功能来定位信息。
        *   `soup.select(...)`: 使用 **CSS 选择器**来定位。这是一种非常强大和灵活的定位方式，例如 `table#assignments-student-table tbody` 的意思是“找到 id 为 `assignments-student-table` 的 `<table>` 标签，再找到它里面的 `<tbody>`”。
        *   `tag.find(...)` / `tag.find_all(...)`: 在一个已经找到的标签内部，继续查找子标签。
    *   **数据清洗**: 使用 `.get_text(strip=True)` 来获取标签内的文本，并用 `strip=True` 去掉前后多余的空格和换行符。使用 `.get("href")` 来获取链接地址。
    *   **智能筛选 (`get_assignments`)**: 这是最精妙的部分。它不是无脑抓取所有作业，而是通过分析作业状态单元格的 CSS 类 (`submissionStatus-complete`) 或文本内容 (`'/' in status_text`) 来判断作业是否已完成，最终只保留未完成的作业。

*   **注意细节 (Details):**
    *   **健壮的选择器**: `get_courses` 中尝试了多个 CSS 选择器 (`course_tags = soup.select(...)` followed by `if not course_tags: ...`)，如果第一个找不到，会尝试第二个。这增加了对网页微小改动的适应性。
    *   **再次强调的防御性编程**: 每个 `find` 操作后，都用 `isinstance(..., Tag)` 进行了检查，防止因网页结构变化导致程序崩溃。
    *   **数据聚合**: `get_assignments` 函数将抓取到的各项信息（名称、链接、状态、截止日期）组装成一个结构清晰的字典 `dict`，然后将这些字典放入一个列表 `list` 中返回。这是处理爬取结果的标准模式。

---

### **模块五：邮件通知 (`send_notification` 函数)**

```python
def send_notification(assignments: list[dict[str, str]]) -> None:
    # ... (函数体)
```

*   **功能 (Function):**
    程序的“嘴巴”。当主程序发现有需要通知的作业时，调用此函数，它会连接到你的邮箱服务器，并发送一封格式化好的提醒邮件。

*   **实现原理 (Principle):**
    *   **配置与代码分离**: 所有敏感信息（邮箱服务器地址、端口、用户名、密码）都通过 `os.getenv()` 从**环境变量**中读取。这是一种安全最佳实践，避免将密码硬编码在代码中。
    *   **构建邮件 (`EmailMessage`)**: 使用 `EmailMessage` 对象来创建一封邮件。可以像设置字典一样方便地设置主题 (`Subject`)、发件人 (`From`) 和收件人 (`To`)。正文通过 `msg.set_content(body)` 设置。
    *   **连接与发送 (`smtplib`)**:
        *   `smtplib.SMTP_SSL(host, port)`: 针对使用 SSL 加密的端口（如 465），在建立连接时就进行加密。
        *   `smtplib.SMTP(host, port)` -> `server.starttls()`: 针对使用 STARTTLS 的端口（如 587），先建立普通连接，然后通过 `starttls()` 命令升级为加密连接。
        *   `server.login(user, password)`: 使用你的邮箱账号和**应用专用密码**登录服务器。
        *   `server.send_message(msg)`: 发送构建好的邮件对象。

*   **注意细节 (Details):**
    *   **环境变量**: 你在复现时，需要在运行脚本前设置这些环境变量。例如，在终端里：`export SMTP_USER="your_email@qq.com"`。
    *   **应用专用密码**: 绝大多数邮箱（如 QQ、163、Gmail）出于安全考虑，不允许直接在第三方程序中使用你的登录密码。你需要在邮箱的设置里开启 SMTP 服务，并生成一个专门给这个爬虫程序使用的“应用专用密码”。
    *   **端口处理**: 代码非常专业地处理了 465 (SSL) 和其他端口 (STARTTLS) 的情况，这增加了它的通用性。
    *   `assert isinstance(...)`: 在检查完环境变量非空后，使用 `assert` 来帮助静态类型检查工具（如 MyPy）确认这些变量的类型，这是一个更现代、更严谨的 Python 写法。

---

### **模块六：主程序入口 (`if __name__ == "__main__":`)**

*   **功能 (Function):**
    这是整个程序的**“总指挥官”或“大脑”**。它定义了程序的执行流程：设置会话 -> 读取配置 -> 登录 -> 获取课程列表 -> 遍历课程获取作业 -> 汇总结果 -> 判断是否需要发送通知 -> 发送通知。

*   **实现原理 (Principle):**
    *   `if __name__ == "__main__":`: 这是 Python 脚本的入口点。只有当你直接运行这个文件时 (`python your_script.py`)，这部分代码才会被执行。如果你把这个文件作为模块导入到其他脚本中，这部分代码不会执行。
    *   **创建 `requests.Session` 对象**: 在所有操作开始前创建一个 `Session` 对象，并设置好 `headers`。这个 `Session` 对象会像一个“有记忆的浏览器”，在后续的所有请求中（登录、获取课程、获取作业）自动携带 cookies，从而保持登录状态。
    *   **逻辑串联**: 它像一条流水线，将前面定义的各个函数（零件）按照正确的顺序组装起来，并负责在它们之间传递数据（例如，将 `login_to_gradescope` 返回的 `logged_in_session` 传递给 `get_courses`）。

*   **注意细节 (Details):**
    *   `session.headers.update(...)`: **非常重要！** 这里设置了 `User-Agent` 请求头，将爬虫伪装成一个真实的 Chrome 浏览器。很多网站会检测 `User-Agent`，如果发现是默认的 `requests` 客户端，可能会拒绝服务或返回不同的内容。
    *   **数据聚合与增强**: 在循环中，它将所有课程的未提交作业汇总到 `all_unsubmitted_assignments` 列表中，并且巧妙地为每个作业字典添加了一个 `course_name` 键，这样在最终的邮件通知里，用户就能知道每个作业属于哪门课。
    *   **条件执行**: 只有在 `logged_in_session` 存在（即登录成功）时，才会执行后续的爬取操作。只有在 `all_unsubmitted_assignments` 列表不为空时，才会调用 `send_notification`。这种层层判断确保了程序的健壮性。

希望这份详尽的分析能帮助你更好地理解并亲手复现这个项目。祝你编码愉快！


当然！这是一个绝佳的学习思路。理解你所使用的“工具”是内化知识的关键。下面，我将为你详细拆解代码中用到的所有外部库的类、函数和方法，就像一份详尽的“工具说明书”。

---

### **1. `requests` 库 (网络交互的瑞士军刀)**

这个库负责所有与互联网服务器的通信。

#### `requests.Session()`
*   **输入值:** 无。
*   **返回值:** 一个 `requests.Session` 对象。
*   **运用方法:**
    你可以把 `Session` 对象想象成一个“有记忆的浏览器实例”。普通 `requests.get()` 每次请求都是独立的，而 `Session` 对象发出的所有请求都共享同一个状态。
    在代码中，`session = requests.Session()` 创建了这个实例。它的最大好处是**自动管理 Cookies**。当你调用 `login_to_gradescope` 成功后，服务器返回的登录凭证 (Cookie) 会被自动保存在 `session` 对象里。之后，所有使用**同一个** `session` 对象发送的请求（如 `get_courses`, `get_assignments`）都会自动带上这个登录凭证，服务器就会认为你是一个已登录的用户。

#### `session.headers.update({...})`
*   **输入值:** 一个字典，键和值都是字符串。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    此方法用于批量更新或添加 `session` 的默认请求头 (Headers)。请求头是附加在网络请求上的一些元信息。最重要的就是 `'User-Agent'`，它告诉服务器“我是谁”。代码中将其设置为一个真实的 Chrome 浏览器标识，这是**伪装爬虫**的关键一步，可以避免被一些简单的反爬机制屏蔽。

#### `session.get(url, timeout, **kwargs)`
*   **输入值:**
    *   `url` (str): 你要访问的网页地址。
    *   `timeout` (int/float, 可选): 超时时间（秒）。如果服务器在这段时间内没有响应，就抛出异常。
*   **返回值:** 一个 `requests.Response` 对象，包含了服务器返回的所有信息。
*   **运用方法:**
    模拟浏览器地址栏输入网址后按回车的操作（GET请求）。在代码的 `safe_request` 函数中，它被用来获取登录页面、课程主页和作业页面的 HTML 内容。

#### `session.post(url, data, timeout, **kwargs)`
*   **输入值:**
    *   `url` (str): 你要提交表单的目标地址，这里是 `LOGIN_URL`。
    *   `data` (dict, 可选): 你要提交的表单数据。在代码中就是包含了邮箱、密码和 token 的 `payload` 字典。
    *   `timeout` (int/float, 可选): 超时时间。
*   **返回值:** 一个 `requests.Response` 对象。
*   **运用方法:**
    模拟在网页上填写表单（如登录框）后点击“提交”按钮的操作（POST请求）。在 `login_to_gradescope` 函数中，它将用户的登录信息发送给服务器以完成登录。

#### `response.text` (Response 对象的属性)
*   **输入值:** 无（它是一个属性，不是方法）。
*   **返回值:** 一个字符串 (str)，包含了服务器返回的网页内容的**HTML源码**。
*   **运用方法:**
    这是连接 `requests` 和 `BeautifulSoup` 的桥梁。`requests` 负责获取原始的 HTML 字符串，然后 `response.text` 将这个字符串交给 `BeautifulSoup` 去解析。

#### `response.raise_for_status()` (Response 对象的方法)
*   **输入值:** 无。
*   **返回值:** 无 (`None`)。但如果 HTTP 状态码表示有错误（如 404 Not Found, 500 Server Error），它会**抛出一个异常**。
*   **运用方法:**
    这是一个非常优雅的错误检查机制。在 `safe_request` 中，调用此方法可以确保只有在请求成功（状态码 2xx）时程序才会继续执行，否则就会被 `try...except` 块捕获，触发重试逻辑。

#### `response.url` (Response 对象的属性)
*   **输入值:** 无。
*   **返回值:** 一个字符串 (str)，表示请求**最终停留**的 URL。
*   **运用方法:**
    登录成功后，服务器通常会**重定向**到一个新页面（比如课程主页）。这个属性获取的是重定向之后的最终 URL。代码通过检查 `response.url` 是否是预期的 `/courses` 或 `/account` 页面，来准确判断登录是否成功。

---

### **2. `bs4` (BeautifulSoup) 库 (HTML 的“解剖刀”)**

这个库负责解析 `requests` 获取到的 HTML 字符串，让你能方便地提取所需信息。

#### `BeautifulSoup(html_string, 'html.parser')`
*   **输入值:**
    *   `html_string` (str): `response.text` 返回的 HTML 源码。
    *   `'html.parser'` (str): 指定使用 Python 内置的解析器。
*   **返回值:** 一个 `BeautifulSoup` 对象（通常命名为 `soup`），它是一个结构化的、可以被搜索的树形对象。
*   **运用方法:**
    这是使用 `BeautifulSoup` 的第一步，将一堆杂乱的字符串转换成一个有组织的“汤”(soup)，为后续的数据提取做准备。

#### `soup.find(name, attrs)`
*   **输入值:**
    *   `name` (str): 你要查找的 HTML 标签名，例如 `'meta'`, `'div'`。
    *   `attrs` (dict, 可选): 一个包含标签属性的字典，用于精确定位。例如 `{"name": "csrf-token"}`。
*   **返回值:** **第一个**匹配条件的 `Tag` 对象；如果找不到，则返回 `None`。
*   **运用方法:**
    用于查找页面上唯一的、关键的元素。在 `login_to_gradescope` 中，它被用来精确地找到那个包含 CSRF token 的 `<meta>` 标签。

#### `soup.select(css_selector)`
*   **输入值:** `css_selector` (str): 一个 CSS 选择器字符串。
*   **返回值:** 一个**列表 (list)**，包含了所有匹配该选择器的 `Tag` 对象。如果一个都找不到，返回一个空列表 `[]`。
*   **运用方法:**
    这是 `BeautifulSoup` 中最强大、最灵活的查找方法。它让你能使用和前端 CSS 一样的语法来定位元素。例如，`.courseBox` 表示查找所有 class 为 `courseBox` 的元素，`a.courseBox` 表示查找 class 为 `courseBox` 的 `<a>` 标签。它被用来批量获取所有课程和所有作业行。

#### `soup.select_one(css_selector)`
*   **输入值:** `css_selector` (str): 一个 CSS 选择器字符串。
*   **返回值:** **第一个**匹配该选择器的 `Tag` 对象；如果找不到，返回 `None`。
*   **运用方法:**
    `select` 的单数版本，相当于 `select(...)[0]`，但更安全（找不到时不会报错）。代码中用它来定位唯一的作业表格主体 `tbody`。

#### `tag.find_all(name, recursive)`
*   **输入值:**
    *   `name` (str): 标签名。
    *   `recursive` (bool, 可选): `recursive=False` 表示只查找该标签的**直接子标签**，而不深入到孙子辈。
*   **返回值:** 一个**列表 (list)**，包含所有匹配的 `Tag` 对象。
*   **运用方法:**
    在 `get_assignments` 中，`table_body.find_all("tr", recursive=False)` 是一个非常聪明的用法。它确保只获取作业表格的第一级 `<tr>`（行），避免了因复杂的 HTML 结构（比如某个作业描述里又包含了一个小表格）而出错。

#### `tag.get(attribute_name)`
*   **输入值:** `attribute_name` (str): 你想获取的 HTML 属性名，例如 `'href'`, `'content'`, `'class'`。
*   **返回值:** 属性的值（通常是字符串或列表）；如果该属性不存在，返回 `None`。
*   **运用方法:**
    用于从一个标签中提取“藏”在属性里的信息。例如，从 `<a>` 标签中用 `.get("href")` 提取链接地址，从 `<meta>` 标签中用 `.get("content")` 提取 token。

#### `tag.get_text(strip=True)`
*   **输入值:** `strip` (bool, 可选): 如果为 `True`，会自动移除返回文本前后多余的空格、制表符和换行符。
*   **返回值:** 一个字符串 (str)，包含了该标签内所有**可见的文本内容**。
*   **运用方法:**
    用于提取用户在浏览器上能看到的文字。例如，用它来获取课程名称、作业标题、截止日期等。`strip=True` 是一个几乎每次都会用到的好习惯，能让提取的数据更干净。

#### `bs4.element.Tag`
*   **运用方法:**
    这是一个**类型**，而不是一个函数。在代码中，它被用于 `isinstance(variable, Tag)` 这样的判断。这是一个防御性编程的典范：在对一个变量（比如 `find` 的返回值）调用 `.get()` 或 `.get_text()` 之前，先用 `isinstance` 检查它到底是不是一个真正的 `Tag` 对象，而不是 `None`。这可以从根本上杜绝因找不到元素而导致的 `AttributeError: 'NoneType' object has no attribute 'get'` 崩溃。

---

### **3. `os` 库 (与操作系统交互)**

#### `os.getenv(key, default=None)`
*   **输入值:**
    *   `key` (str): 你要获取的环境变量的名称，例如 `'SMTP_HOST'`。
    *   `default` (可选): 如果找不到该环境变量，返回的默认值。
*   **返回值:** 环境变量的值（字符串）；如果不存在，则返回 `default`（默认为 `None`）。
*   **运用方法:**
    这是代码**安全性**和**可配置性**的核心。它允许你将账号、密码等敏感信息或可变配置（如收件人地址）存储在操作系统环境中，而不是硬编码在代码里。这样，你的代码可以安全地分享给他人，而每个人只需配置好自己的环境变量即可运行。

---

### **4. `smtplib` 与 `email.message` 库 (邮件发送双人组)**

#### `email.message.EmailMessage()`
*   **输入值:** 无。
*   **返回值:** 一个 `EmailMessage` 对象。
*   **运用方法:**
    创建一个空白的邮件“容器”。你可以把它想象成一封空邮件，接下来要往里面填东西。

#### `msg['Header'] = value`
*   **运用方法:**
    这个对象用起来像字典。你可以直接用方括号语法来设置邮件的**信头 (Headers)**。
    *   `msg["Subject"] = "邮件主题"`
    *   `msg["From"] = "发件人地址"`
    *   `msg["To"] = "收件人地址"`

#### `msg.set_content(body)`
*   **输入值:** `body` (str): 邮件的正文内容。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    将你拼接好的邮件正文（在代码中是 `"\n".join(lines)`）填充到邮件容器里。

#### `smtplib.SMTP_SSL(host, port, timeout)`
*   **输入值:**
    *   `host` (str): SMTP 服务器地址（从环境变量读取）。
    *   `port` (int): 端口号，SSL 加密通常是 465。
    *   `timeout` (int, 可选): 连接超时时间。
*   **返回值:** 一个 `SMTP_SSL` 服务器连接对象。
*   **运用方法:**
    与需要 SSL 加密的邮件服务器建立一个安全的连接。

#### `smtplib.SMTP(host, port, timeout)`
*   **输入值:** 同上，但端口通常是 587 或 25。
*   **返回值:** 一个 `SMTP` 服务器连接对象。
*   **运用方法:**
    与邮件服务器建立一个普通的、未加密的连接。这个连接稍后需要通过 `starttls()` 升级为加密连接。

#### `server.starttls()`
*   **输入值:** 无。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    对一个已建立的普通 `SMTP` 连接，发送 `STARTTLS` 命令，将其**升级为加密连接**。这是现代邮件服务器推荐的安全做法。

#### `server.login(user, password)`
*   **输入值:**
    *   `user` (str): 你的邮箱用户名。
    *   `password` (str): **注意！** 这里通常不是你的邮箱登录密码，而是在邮箱设置中生成的**“应用专用密码”**。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    向邮件服务器验证你的身份。

#### `server.send_message(msg)`
*   **输入值:** `msg` (EmailMessage): 之前构建好的 `EmailMessage` 对象。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    将整封邮件发送出去。

#### `server.close()`
*   **输入值:** 无。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    断开与邮件服务器的连接。代码中使用 `finally` 块来确保无论发送成功与否，连接最终都会被关闭，这是一种很好的资源管理习惯。

---

### **5. `time` 库 (时间掌控者)**

#### `time.sleep(seconds)`
*   **输入值:** `seconds` (int/float): 需要程序暂停的秒数。
*   **返回值:** 无 (`None`)。
*   **运用方法:**
    让程序“睡一会儿”。在 `safe_request` 函数中，当一次网络请求失败后，它会调用 `time.sleep()` 等待一小段时间再进行下一次重试，这被称为**“退避”(backoff)**，可以减轻对目标服务器的压力。

希望这份超详细的“说明书”能让你在复现代码时，对每一步都了然于胸，真正把这些知识变成你自己的技能！

> can we try to launch it on QQ ?

当然可以！你提出的这个问题非常好，将这个自动化工具部署到国内用户最常用的 QQ 平台上，是让它真正变得“实用”的关键一步。

**答案是：完全可行！** 在 QQ 平台部署 Bot 是一个非常成熟的领域，只不过它的实现方式和 Telegram 有着本质的不同。

### **核心挑战：QQ 的“封闭”生态**

首先，你需要理解一个关键区别：
*   **Telegram:** 官方提供了极其开放和强大的 Bot API。你的 Python 脚本可以直接通过 HTTP 请求与 Telegram 服务器对话，非常简单直接。
*   **QQ:** 官方的 Bot API 门槛很高，主要面向企业，需要繁琐的审核，不适合个人项目。因此，社区发展出了一套基于**“逆向工程”**的**非官方协议**来实现个人 Bot。

这意味着我们的方案需要一个“中间人”来模拟一个真实的 QQ 客户端。

### **现代 QQ Bot 的黄金搭档：`NoneBot2` + `Go-CQHTTP`**

这是目前在国内开发 QQ Bot 最主流、最稳定、功能最强大的技术栈。让我们用一个比喻来理解它们的关系：

*   **`Go-CQHTTP` (中间人/翻译官):** 这是一个独立的可执行程序（用 Go 语言编写，性能很高）。
    *   **它的工作：** 负责登录你的 Bot QQ 账号，并处理所有与腾讯服务器的底层网络通信。它就像 Bot 的“**耳朵和嘴巴**”。
    *   **对外：** 它会把从 QQ 服务器收到的所有消息（比如好友私聊、群消息）转换成一种标准的、程序能听懂的格式（称为 OneBot 标准），然后发送出来。
    *   **对内：** 它会监听一个地址，等待你的 Python 程序告诉它要“说什么话”，然后它再把这些话转换成 QQ 协议发给腾讯服务器。

*   **`NoneBot2` (你的 Python 大脑):** 这是一个功能强大的异步 Python Bot 框架。
    *   **它的工作：** 负责处理所有上层逻辑。它就像 Bot 的“**大脑**”。
    *   **对内：** 它连接到 `Go-CQHTTP`，接收 `Go-CQHTTP` 传来的消息。
    *   **处理：** 你在这个框架里编写 Python 代码，定义各种规则，比如“当收到‘/查询作业’这个指令时，应该做什么”。
    *   **对外：** 处理完逻辑后，它会告诉 `Go-CQHTTP`：“请回复给这个用户‘你还有3个作业没交’”。

**总结：`Go-CQHTTP` 负责登录和通信，`NoneBot2` 负责思考和响应。它们俩协同工作，构成一个完整的 QQ Bot。**

---

### **部署你的 Gradescope Bot 的步骤**

#### **第一步：准备工作**

1.  **注册一个专门的 Bot QQ 小号！**
    **极其重要！** 由于使用的是非官方协议，有极小的概率被腾讯风控。**绝对不要**用你的主力 QQ 号来做 Bot，一定要用一个不重要的小号。
2.  **准备一个 24/7 运行的环境。**
    Bot 需要一直在线。你可以使用：
    *   一台云服务器 (VPS)，比如阿里云、腾讯云的学生机。
    *   一台树莓派 (Raspberry Pi)。
    *   一台你自己的旧电脑，保持开机。

#### **第二步：安装并配置 `Go-CQHTTP` (耳朵和嘴巴)**

1.  **下载：** 前往 `Go-CQHTTP` 的 [GitHub Releases 页面](https://github.com/Mrs4s/go-cqhttp/releases)，根据你的服务器系统下载对应的可执行文件。
2.  **首次运行：** 在服务器上运行它，它会自动生成 `config.yml` 配置文件。
3.  **配置 `config.yml`：**
    *   `uin`: 填入你的 Bot QQ 小号。
    *   `password`: 填入 Bot 的密码。
    *   `servers`: 这是**最关键**的配置，用来和 `NoneBot2` 通信。推荐使用 WebSocket 方式。配置如下：
        ```yaml
        servers:
          # 正向 Websocket
          - ws:
              # 正向WS服务器监听地址
              host: 127.0.0.1
              # 正向WS服务器监听端口
              port: 8080
        ```
4.  **再次运行 `Go-CQHTTP`：** 它可能会提示你需要扫码或滑动验证码登录。登录成功后，它就会显示“连接到 … successfully”，并开始监听来自 `NoneBot2` 的连接。

#### **第三步：创建并编写 `NoneBot2` 项目 (大脑)**

1.  **安装脚手架：** 在你的服务器上安装 `nb-cli`。
    ```bash
    pip install nb-cli
    ```
2.  **创建项目：** 使用脚手架快速创建一个 `NoneBot2` 项目。
    ```bash
    nb create
    ```
    在引导过程中，选择 `onebot.v11` (OneBot V11) 作为适配器。
3.  **配置 `.env` 文件：** 在生成的项目文件夹里，找到 `.env` 文件，配置 `NoneBot2` 去连接 `Go-CQHTTP`。
    ```
    # .env 文件
    HOST=127.0.0.1
    PORT=8080 # 这里的端口要和 go-cqhttp 里配置的一样
    ```
4.  **编写你的插件逻辑：**
    *   在项目 `src/plugins` 目录下创建一个新的 python 文件，比如 `gradescope_checker.py`。
    *   在这里编写响应用户指令的代码。

**示例代码 (`gradescope_checker.py`)**

```python
from nonebot import on_command
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11 import MessageEvent, PrivateMessageEvent
from nonebot.params import ArgPlainText

# 假设你已经把数据库操作和爬虫逻辑封装好了
# from .utils import db, scraper

# --- 创建指令处理器 ---
# 当用户发送 "/绑定 email password" 时触发
set_credentials = on_command("绑定", priority=5)

@set_credentials.handle()
async def handle_first_receive(matcher: Matcher, event: PrivateMessageEvent, args: str = ArgPlainText()):
    # args 就是用户在 "/绑定" 后面输入的所有内容
    if not args:
        await matcher.pause("请输入你的 Gradescope 邮箱和密码，用空格隔开。")
    
    parts = args.split()
    if len(parts) != 2:
        await matcher.finish("格式错误！请输入‘邮箱 密码’，例如：/绑定 my@email.com mypassword")

    email, password = parts
    user_id = event.user_id  # 获取用户的 QQ 号

    # --- 在这里调用你的数据库逻辑 ---
    # 比如：db.save_credentials(user_id, email, password)
    # 注意：一定要加密存储！
    
    await matcher.finish(f"绑定成功！你的邮箱是: {email}。我会开始为你检查作业。")


# --- 创建查询指令 ---
check_assignments = on_command("查询作业", priority=5)

@check_assignments.handle()
async def handle_check(event: PrivateMessageEvent):
    user_id = event.user_id
    
    await check_assignments.send("正在为你查询，请稍候...")
    
    # --- 在这里调用你的爬虫逻辑 ---
    # credentials = db.get_credentials(user_id) # 解密获取凭证
    # new_assignments = scraper.run(credentials['email'], credentials['password'])
    
    # 模拟结果
    new_assignments = [{"course_name": "CS101", "name": "Homework 5"}]

    if new_assignments:
        # 这里可以调用你的邮件/消息格式化逻辑
        response_text = f"发现 {len(new_assignments)} 个新作业：\n"
        for assignment in new_assignments:
             response_text += f" - 课程: {assignment['course_name']}, 作业: {assignment['name']}\n"
        await check_assignments.finish(response_text)
    else:
        await check_assignments.finish("太棒了！目前没有未提交的作业。")

# --- 别忘了还有自动定时任务！---
# 你可以使用 nonebot-plugin-apscheduler 插件来实现
```

#### **第四步：运行 Bot**

1.  确保你的 `Go-CQHTTP` 正在一个终端窗口里运行。
2.  打开**另一个**终端窗口，进入你的 `NoneBot2` 项目目录，运行 `nb run`。
3.  如果没有报错，你的“大脑”就成功连接上了“耳朵和嘴巴”。
4.  现在，用你的大号 QQ 给你的 Bot 小号发送私聊消息 “/绑定 xxx yyy”，看看它会不会回复你！

这个方案的初始配置比 Telegram 略复杂，但一旦搭建完成，`NoneBot2` 框架的强大功能和丰富的社区插件会让你觉得物超所值。祝你成功！

> environment variables:
$env:GRADESCOPE_EMAIL = "chensh2025@shanghaitech.edu.cn"  
$env:GRADESCOPE_PASSWORD = "320105200704223412"  
$env:SMTP_HOST = "smtp.qq.com"  
$env:SMTP_PORT = "465"  
$env:SMTP_USER = "1123562283@qq.com"  
$env:SMTP_PASSWORD = "iaozyvcggojligga"  
$env:SMTP_FROM = "1123562283@qq.com"  
$env:SMTP_TO = "chensh2025@shanghaitech.edu.cn"