# 采购信息解析模块开发规范

## 1. 概述

本文档旨在为新的省份采购信息解析模块提供统一的开发规范和接口标准。所有新模块**必须**严格遵守此规范，以确保能与主程序 (`main.py`) 无缝集成，无需对主程序进行任何修改。

本文档以 `chongqing.py` 和 `jiangsu.py` 的最终成功版本为蓝本。

## 2. 文件与目录结构

- 所有省份解析模块都必须放置在 `detail_parsers/` 目录下。
- 模块文件名必须为省份的汉语拼音小写，例如：`shandong.py`, `guangdong.py`。

## 3. 模块内部结构

每个省份的解析模块 (`.py` 文件) 必须包含以下三个核心组件：
1.  两个解析器类 (一个处理地方公告，一个处理中央公告)。
2.  一个 `get_parser_for_url(url)` 函数。
3.  一个 `get_dynamic_html(url, parser_type)` 函数。

---

### 3.1 解析器类 (Parser Classes)

每个模块必须定义两个类，分别用于解析地方公告和中央公告。

-   **命名规范**: `[ProvinceName]LocalGovParser` 和 `[ProvinceName]CentralGovParser`，例如 `ShandongLocalGovParser`。
-   **核心方法**: 每个类必须实现一个 `parse(self, html: str)` 方法。

#### `parse(self, html: str)` 方法详解

-   **参数**:
    -   `html (str)`: 由 `get_dynamic_html` 函数获取到的、包含完整动态内容的页面HTML字符串。
-   **返回值**:
    -   必须返回一个 **列表 (list)**，即使只解析出一条数据。
    -   列表中的每个元素都是一个 **字典 (dict)**，代表一条中标信息。
    -   如果页面没有解析到任何有效的标的信息，方法应返回一个空列表 `[]`。

-   **返回字典的字段规范 (重要！)**:
    -   返回的字典**必须**包含以下 **11个** key，且key的名称必须完全一致。
    -   如果某个字段在页面上无法找到，其 value 必须设置为字符串 `'N/A'`。
    -   **严禁**在 `parse` 方法的返回字典中包含 `链接` 或 `省份` 字段，这两个字段由主程序 `main.py` 统一添加。

    ```python
    # 必须包含的11个字段
    {
        "发布日期": "YYYY年MM月DD日" or "N/A",
        "项目号": "xxxx" or "N/A",
        "采购方式": "公开招标" or "N/A",
        "项目名称": "xxxx" or "N/A",
        "供应商名称": "xxxx" or "N/A",
        "中标金额": "xxxx" or "N/A",
        "名称": "货物名称" or "N/A", # 主要标的物名称
        "品牌": "xxxx" or "N/A",
        "规格型号": "xxxx" or "N/A",
        "数量": "x台" or "N/A",
        "单价": "xxxx元" or "N/A"
    }
    ```

---

### 3.2 `get_parser_for_url(url)` 函数

这是模块被主程序调用的入口之一。

-   **功能**: 根据传入的公告详情页 `url`，判断其类型（中央或地方），并返回对应解析器类的一个**实例**。
-   **函数签名**: `def get_parser_for_url(url: str):`
-   **实现逻辑与最佳实践**:
    - **首选策略**: 优先使用公告来源网站的**独特域名** (例如, `ccgp-jiangsu.gov.cn`) 作为判断地方公告的依据。这比判断URL路径更可靠、更精确。
    - **备用策略**: 如果没有独特域名，再考虑检查URL路径中是否包含 `/dfgg/` (地方) 或 `/zygg/` (中央) 等特征片段。
-   **返回值**:
    -   如果 `url` 是地方公告，返回 `[ProvinceName]LocalGovParser()` 的实例。
    -   如果 `url` 是中央公告，返回 `[ProvinceName]CentralGovParser()` 的实例。
    -   如果无法判断类型，返回 `None`。

---

### 3.3 `get_dynamic_html(url, parser_type)` 函数

这是模块被主程序调用的另一个入口。

-   **功能**: 使用 Selenium 和 WebDriver 获取指定 `url` 的动态HTML内容。
-   **函数签名**: `def get_dynamic_html(url, parser_type='local'):`
    -   **注意**: `parser_type` 参数是为了兼容主程序 `main.py` 的调用而保留的，即使在模块内部两个类型的页面等待逻辑完全相同，也**必须保留**此参数。
-   **实现逻辑**:
    -   初始化 Selenium WebDriver。
    -   `driver.get(url)`
    -   使用 `WebDriverWait` 等待页面关键元素加载完成（例如 `body` 或某个特定的容器 `div`）。
    -   返回 `driver.page_source`。
    -   在 `finally` 块中确保 `driver.quit()` 被调用。

## 4. 模块代码模板

以下是一个可供复制和修改的完整模块模板。开发者需要填充 `... # TODO: ...` 部分的逻辑。

```python
# detail_parsers/template.py

from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

# 开发者无需修改 BaseParser
class BaseParser:
    def parse(self, html: str):
        raise NotImplementedError

# --- 地方公告解析器 ---
class TemplateLocalGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []
        
        # ... TODO: 在这里编写地方公告的解析逻辑 ...
        
        # 示例：
        # parsed_item = {
        #     "发布日期": "N/A",
        #     "项目号": "N/A",
        #     # ... (所有11个字段)
        # }
        # results.append(parsed_item)

        return results

# --- 中央公告解析器 ---
class TemplateCentralGovParser(BaseParser):
    def parse(self, html: str):
        soup = BeautifulSoup(html, 'lxml')
        results = []

        # ... TODO: 在这里编写中央公告的解析逻辑 ...

        return results

# --- 模块必要函数 (开发者需按需修改类名) ---
def get_parser_for_url(url: str):
    """根据URL返回合适的解析器实例"""
    if "/dfgg/" in url:
        return TemplateLocalGovParser() # 注意修改类名
    elif "/zygg/" in url:
        return TemplateCentralGovParser() # 注意修改类名
    return None

def get_dynamic_html(url, parser_type='local'):
    """获取动态HTML，函数签名和基础逻辑保持不变"""
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_experimental_option('excludeSwitches', ['enable-logging'])
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "body"))
        )
        html = driver.page_source
    except TimeoutException:
        print(f"页面加载超时: {url}")
        html = None
    finally:
        if driver:
            driver.quit()
    return html
``` 