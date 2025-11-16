# 1. 导入两个库
import requests
from bs4 import BeautifulSoup

# 2. 定义你要爬取的网址
url = 'https://www.gradescope.com/courses/1132878'

try:
    # 3. 使用 requests 发送网络请求，获取网页内容
    response = requests.get(url)
    response.raise_for_status() # 如果请求失败 (例如 404, 500), 会抛出异常

    # 4. 使用 BeautifulSoup 解析网页内容
    #    - response.text 是网页的 HTML 源码
    #    - 'html.parser' 是 Python 内置的解析器
    soup = BeautifulSoup(response.text, 'html.parser')

    # 5. 从解析后的对象中提取信息，例如网页标题
    page_title = soup.title.string
    print(f"网页的标题是: {page_title}")

except requests.exceptions.RequestException as e:
    print(f"请求网页时出错: {e}")