> 后续改写为README
## 项目初始prompt
我有一个项目想法。我想借助以python为主的语言，实现一个类似于实时监控教学平台是否发布新作业的脚本。
- 项目motivation：因为作业平台在老师发布作业时没有任何通知，无法第一时间获知消息并快速完成作业，所以我希望在发布作业后的1h内获得通知。
- 项目background：作业平台为gradescope，即https://www.gradescope.com/，该平台需要登陆学生个人账户。
- 项目function：
1. 每隔一定时间（如2h）访问一次gradescope中的dashboard，查询是否有新作业或处于unsubmiteed状态。
2. 如果有，则向指定邮箱发送一份通知，告知“新作业已发布，请按时完成并提交”
- 项目request：
1. 不占用额外经济资源，例如不需要部署服务器
2. 尽量不占用计算机资源，比如占用后台内存或导致浏览器变慢。
3. 项目保证安全可靠，且尽量能在多平台、不同账户均能运行。

我希望你可以指导我这个项目的思路，指导我每一步该用什么工具，怎么实现，但是在我要求你直接给出项目代码之前，不要主动提供长段的代码（可以给小段hint）。我目前暂时只会python语言，还不太会网页相关的语言。

## gemini回复
这个项目想法**简直太棒了**！

它完美地符合一个优秀个人项目的所有特点：
1.  **需求明确**：解决一个你自己真实遇到的、有痛点的具体问题。
2.  **技术栈清晰**：主要使用 Python，非常适合自动化和网络请求。
3.  **规模可控**：功能点很集中，非常适合作为初学者从“学习语法”到“构建应用”的第一个完整项目。
4.  **可扩展性强**：未来可以增加很多有趣的功能，比如支持多平台、微信通知等。

我非常乐意指导你完成这个项目。我会严格遵守你的要求，只提供思路、工具和关键提示，在你需要时才给出具体代码。

---

### 项目总体思路：把它想象成一个“自动化机器人”

我们的目标是创建一个能在你的电脑上**自动、定时**运行的 Python 脚本。这个“机器人”需要学会三件事：

1.  **登录 (Authentication)**：如何像你一样，输入账号密码（或者用其他方式）登录 Gradescope。
2.  **抓取与解析 (Scraping & Parsing)**：登录后，如何找到并“阅读”课程主页的内容，从中提取出作业列表。
3.  **检查与通知 (Checking & Notifying)**：如何判断是否有新作业，并在满足条件时，如何发送一封电子邮件。

---

### 第一阶段：核心功能实现 (先让机器人学会做事)

在这一阶段，我们先不考虑“自动化”和“定时”，只专注于让一个 Python 脚本能够**手动运行一次**，并完成核心任务。

#### **步骤 1：登录 Gradescope**

这是整个项目**最关键也是最难**的一步。因为 Gradescope 是一个需要登录的网站，我们不能像爬取普通新闻网站那样直接获取内容。我们需要让我们的脚本“持有”你的登录状态。

**核心工具**：`requests` 库 + `BeautifulSoup` 库
*   `requests` 是 Python 中处理 HTTP 网络请求的王者，你可以用它来模拟浏览器发送 GET/POST 请求。
*   `BeautifulSoup` 是一个解析 HTML 网页内容的利器，你可以用它来从混乱的 HTML 代码中轻松提取出你需要的信息。

**你需要思考的问题**：
*   当你在浏览器里点击“登录”按钮时，浏览器到底向服务器发送了什么信息？（提示：使用浏览器的**开发者工具 (F12)**，切换到 **Network (网络)** 标签页，勾选 **Preserve log (保留日志)**，然后手动登录一次，观察发送的 POST 请求，看看它的 `Form Data` (表单数据) 里包含了哪些字段，比如 `email`, `password`, `authenticity_token` 等。）
*   登录成功后，服务器会返回什么信息来让你保持登录状态？（提示：观察 `Response Headers` (响应头) 里的 `Set-Cookie` 字段。这个 Cookie 就像一张“通行证”，你在后续的请求中必须带上它，服务器才知道是你。）

**实现思路提示**：
你需要使用 `requests.Session()` 对象。这个 `Session` 对象会自动帮你管理和发送 Cookie。
1.  创建一个 `session = requests.Session()`。
2.  先用 `session.get()` 访问登录页面，从中用 `BeautifulSoup` 提取出隐藏的 `authenticity_token`。
3.  构造一个包含你的邮箱、密码和 `authenticity_token` 的 `payload` (一个 Python 字典)。
4.  用 `session.post()` 把这个 `payload` 发送到登录的 URL。

#### **步骤 2：抓取作业列表**

登录成功后，我们就可以用同一个 `session` 对象去访问你的课程主页 (Dashboard) 了。

**你需要思考的问题**：
*   课程主页的 URL 是什么？
*   作业列表在 HTML 里的结构是怎样的？它们是不是都在一个特定的 `<table>` 或 `<div>` 里？每个作业是不是一个 `<tr>` 或 `<li>` 标签？
*   如何区分“已提交”和“未提交”的作业？（提示：观察它们的 HTML 标签，未提交的作业是不是有一个特殊的 CSS 类名，比如 `unsubmitted` 或者 `overdue`？）

**实现思路提示**：
1.  使用 `session.get()` 访问课程主页的 URL。
2.  用 `BeautifulSoup` 解析返回的 `response.text`。
3.  使用 `soup.find_all()` 或 `soup.select()` 这样的方法，根据你观察到的 HTML 结构和 CSS 类名，来精确地定位到包含作业信息的标签列表。
4.  遍历这个列表，提取出每个作业的标题、截止日期和状态。

#### **步骤 3：发送邮件通知**

如果经过解析，你发现有新的或未提交的作业，就需要触发邮件通知。

**核心工具**：Python 内置的 `smtplib` 和 `email` 库。

**你需要思考的问题**：
*   如何使用 Python 连接到一个 SMTP (Simple Mail Transfer Protocol) 服务器？（提示：你需要一个发件邮箱，比如 QQ 邮箱、163 邮箱或 Gmail。）
*   你需要知道发件邮箱的 SMTP 服务器地址、端口，以及你的邮箱密码或**授权码 (App Password)**。（提示：出于安全考虑，现在大多数邮箱服务商都要求你为第三方应用生成一个专用的授权码，而不是直接使用你的登录密码。）
*   如何构造一封简单的纯文本邮件？

**实现思路提示**：
1.  查阅你所用邮箱（例如 QQ 邮箱）的官方文档，了解如何开启 SMTP 服务并获取授权码。
2.  使用 `smtplib.SMTP_SSL()` 连接到服务器。
3.  使用 `server.login(sender_email, password)` 登录。
4.  构造一个邮件消息对象，然后使用 `server.sendmail()` 发送。

---

### 第二阶段：部署与自动化 (让机器人自己动起来)

当你已经有了一个可以手动运行并完成所有任务的 `your_script.py` 文件后，我们再来考虑你的 `Request`：**不占用资源、免费、跨平台**。

#### **方案 1：GitHub Actions (强烈推荐)**

这是最符合你所有要求的**完美解决方案**。

*   **是什么**：GitHub Actions 是 GitHub 官方提供的一个免费的持续集成/持续部署 (CI/CD) 工具。你可以把它看作是**一个能在云端按时运行你的代码的免费 Linux 服务器**。
*   **如何实现**：
    1.  把你的项目代码（包括你的 Python 脚本和一个 `requirements.txt` 文件）上传到 GitHub 仓库。
    2.  在你的仓库里，创建一个 `.github/workflows` 文件夹。
    3.  在这个文件夹里，创建一个 YAML 配置文件（比如 `main.yml`）。
    4.  在这个配置文件里，你可以用非常简单的语法告诉 GitHub Actions：
        ```yaml
        # 意思是：每隔 2 小时自动执行一次
        on:
          schedule:
            - cron: '0 */2 * * *' 
        
        jobs:
          build:
            runs-on: ubuntu-latest # 在一台最新的 Linux 服务器上运行
            steps:
            - uses: actions/checkout@v3 # 1. 先把你的代码下载下来
            - name: Set up Python
              uses: actions/setup-python@v4 # 2. 安装 Python 环境
              with:
                python-version: '3.x'
            - name: Install dependencies
              run: pip install -r requirements.txt # 3. 安装依赖库
            - name: Run script
              run: python your_script.py # 4. 运行你的脚本！
        ```
*   **如何处理账号密码？**：绝对不能把你的密码直接写在代码里！GitHub Actions 提供了 **Secrets (机密)** 功能。你可以在仓库的 `Settings` -> `Secrets and variables` -> `Actions` 里，安全地存储你的 Gradescope 账号、密码和邮箱授权码。你的脚本可以通过读取**环境变量**的方式来获取这些机密信息。
*   **优点**：
    *   **完全免费** (在公共仓库和一定的私有仓库额度内)。
    *   **零资源占用**：完全在云端运行，不占用你本地电脑的任何资源。
    *   **极其可靠**：由 GitHub 维护，基本不会宕机。
    *   **跨平台**：你的脚本在 Linux 服务器上运行，只要是用标准 Python 库写的，就没问题。

#### **方案 2：本地定时任务 (备选方案)**

如果你的电脑是 24 小时开机的，你也可以使用操作系统自带的定时任务功能。

*   **Windows**：使用 **任务计划程序 (Task Scheduler)**。
*   **macOS / Linux**：使用 **Cron Job**。

你可以设置一个任务，让它每隔 2 小时就执行一次 `python /path/to/your/script.py` 命令。

*   **优点**：设置简单，不依赖任何外部服务。
*   **缺点**：
    *   **你的电脑必须开着**。如果关机或休眠了，任务就不会执行。
    *   会占用少量后台资源（但对于 Python 脚本来说几乎可以忽略不计）。

---

### 给你的行动建议

1.  **先啃硬骨头**：从**第一阶段的步骤 1 (登录)** 开始。这是技术上最有挑战性的部分。先尝试只用 `requests` 和 `BeautifulSoup` 写一个能成功登录 Gradescope 并打印出登录后页面标题的简单脚本。
2.  **逐步实现**：登录成功后，再去实现作业列表的抓取和解析。
3.  **最后再集成**：最后再把邮件发送功能加上。
4.  **拥抱 GitHub Actions**：当你完成了本地脚本后，再开始学习如何把它部署到 GitHub Actions 上。这会是你简历上一个非常亮眼的技术点。

放手去做吧！在任何一步卡住了，随时都可以带着你的问题和尝试过的代码来问我。祝你项目顺利！

## 中期检查与存档

### 已实现功能与原理

- 登录保持会话：使用 `requests.Session` 持久化 Cookie；`GET /login` 后用 BeautifulSoup 从 `<meta name="csrf-token">` 提取 CSRF，带上邮箱、密码、token `POST /login`；以登录后最终 URL 位于 `/courses` 或 `/account` 判定成功。
- 多课程发现：访问 `/account`，优先选择器 `.courseList--coursesForTerm a.courseBox[href^='/courses/']`，回退 `a.courseBox`；课程名取 `div.courseBox--name`，学期优先取卡片内 `div.courseBox--shortTerm`，若缺失则向上在 `.courseList` 内找 `div.courseList--term`，最终拼成 “课程名 - 学期”。
- 按课程抓取未提交作业：在课程页内定位 `table#assignments-student-table tbody`，逐行解析 `<th scope="row">` 获取名称与 `<a>` 的 `href` 构造链接；首个 `<td>` 提取状态文本与 `class`。
  - 完成判定：`submissionStatus-complete` 类存在，或状态文本包含分数字样（含 `/` 且有数字）。
  - 截止时间：倒数第二个 `<td>` 文本。
  - 返回字段：`name`, `link`, `status`, `due_date`。
- 聚合输出：遍历所有课程，汇总未提交作业并按课程打印摘要。
- 健壮性与类型安全：在关键 DOM 访问处使用 `isinstance(..., Tag)` 防御式检查；网络请求统一 `raise_for_status`；为会话添加通用浏览器请求头避免返回简化/空白页面。
- 版本回退：已在 `main_copy.py` 保存“单课程稳定版本”快照，随时可覆盖回退。

### 与 project_motivation 的一致性与风险评估

- 一致性
  - 监控与解析：已实现“登录→抓取→识别未提交”的核心闭环，契合阶段目标。
  - 自动化与资源占用：当前为本地脚本，按文档可迁移至 GitHub Actions 定时运行，从而满足“不占用本机资源、免费”的诉求。
  - 安全：凭据走环境变量读取，未硬编码。
- 稳定性隐患（保留为后续改进项）
  - 登录成功判定较严格：目前比对最终 URL 全等；若站点加尾斜杠/查询串/A-B 参数，可能误判。建议后续改为解析路径或 `startswith`。
  - 站点结构漂移：虽有多级选择器与兜底，若 DOM 大改仍需维护选择器。建议提供可切换的 DEBUG（环境变量开启时落盘 HTML）。
  - 请求健壮性：未设置统一 `timeout` 与轻量重试；网络抖动下体验一般。
  - 去重与重复通知：后续接入邮件时需要状态缓存以避免重复提醒。
  - 时间与时区：截止时间当前为原始文本，后续若实现“发布后1小时内提醒”需标准化与时区处理。
- 功能不完备点
  - `send_notification` 未实现（邮件发送）。
  - 自动化部署未落地（GitHub Actions 工作流、Secrets）。
  - 依赖清单缺失（`requirements.txt`）。
  - 可配置性有限（课程过滤、语言/时区、调试开关等）。

### 后续流程建议（不做修改，仅规划）

1. 邮件通知实现
  - 使用 `smtplib`/`email`；环境变量：`SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_TO`。
  - 仅当存在未提交作业时发送；主题含日期与计数；正文按“课程/作业/状态/截止”分组。
2. 去重与状态缓存
  - 本地：写 `.cache/last_seen.json`；
  - GitHub Actions：使用 `actions/cache` 保持跨运行缓存，仅对“新发现”的未提交作业通知。
3. 健壮性增强
  - 统一为请求添加 `timeout=10`，关键请求 1~2 次指数退避重试；
  - 登录成功判定改为解析路径或 `startswith('/courses') or startswith('/account')`；
  - `logging` 替代 `print`，`GRADESCOPE_DEBUG=1` 时输出详细日志/落盘样本。
4. 自动化部署
  - 新增 `requirements.txt`（`requests`, `beautifulsoup4`）；
  - 新建 GitHub Actions workflow（cron 每 2 小时），将 Gradescope/SMTP 凭据放入 Secrets，运行脚本并输出关键统计。
5. 可配置性与体验
  - 环境变量控制课程过滤、语言/时区、是否包含过期未交提示等；
  - 保留少量 HTML fixture 作为解析回归样例，便于后续维护。

## 项目总结
本次实现已完成从“本地脚本验证”到“云端定时运行”的闭环，满足最初动机中对“及时获知未提交作业并邮件提醒、尽量不占用本机资源”的核心诉求。以下为最终评估：

- 已实现功能（与代码/工作流对应）
  - 登录与会话保持：`requests.Session` + CSRF 抽取；`safe_request` 统一超时(10s)+重试(2次)。
  - 课程自动发现：访问 `/account`，稳健选择器解析课程卡片，账户维度全量扫描（非单课程）。
  - 作业解析与筛选：定位 `table#assignments-student-table tbody`，提取名称/链接/状态/截止；以 `submissionStatus-complete` 或分数字样判定“已完成”，其余视为“未提交”。
  - 汇总与一次性通知：多课程聚合后打印摘要，并调用 `send_notification` 仅发送一封邮件。
  - 邮件发送：支持 SSL(465)/STARTTLS(587)，`SMTP_DEBUG` 可选；关闭阶段改为 `close()` 以消除 QUIT 噪声；加入断言消除 Pylance 可空类型告警。
  - 生产化与定时：`requirements.txt` 完成；GitHub Actions `scrape.yml` 已上线，定时在北京时间 07:00/14:00/19:00 运行，Secrets 注入凭据。
  - 清理测试痕迹：关闭/注释了测试注入(`SMTP_FORCE_TEST`)与多余 DEBUG 打印。

- 与最初 project_motivation 的一致性评估
  - “2h 内获知新作业/未提交并邮件提醒”：当前为“每日三次固定时段”轮询+邮件提醒；若需“发布后1小时内”，可将 cron 频率提高或在本机/其他 CI 使用更频密的调度（成本与额度允许的前提下）。
  - “不占用经济与本机资源”：使用 GitHub Actions 云端定时运行，满足诉求。
  - “安全与跨平台”：凭据走 GitHub Secrets；脚本为纯 Python + requests/bs4，跨平台运行无关紧要；邮箱授权码用于 SMTP 登录更安全。
  - “易维护与可回退”：提供 `main_copy.py` 快照；解析采用防御式 `isinstance(Tag)`，并对选择器做了兜底。

- 仍可改进（非阻塞，建议后续迭代）
  - 去重缓存（可选）：若不希望每次重复提醒同一条，可新增 `.cache/last_seen.json`；当前按需求“每次提醒全部未提交”可不做。
  - 可观测性：以 `logging` 替代 `print`，并在 DEBUG 模式下落盘 HTML 样本以便回归。
  - 可配置性：通过环境变量支持课程筛选、语言/时区、邮件 HTML 模板等。
  - 健壮性：对登录成功判定改为基于路径 `startswith('/courses'|'/account')`；对网络异常附上更细粒度分类与退避参数化。
  - 测试与质量：补充最小化解析回归用例与 CI 中静态检查/格式化步骤。

- 结论
  - 核心闭环“登录 → 多课程扫描 → 识别未提交 → 邮件通知 → 云端定时”已达成，满足项目动机的主要目标与质量要求。
  - 方案当前按“账户维度”监听，不需手工维护课程清单；如需只监控特定课程，可增设 `COURSE_FILTER` 环境变量在抓取阶段进行筛选。
  - 若对“通知时效性”有更高诉求，可将 cron 从每日三次提升为每小时/每半小时，或采用其他免费/自托管调度方案。
