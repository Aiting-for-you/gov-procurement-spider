# 政府采购网解析器模块开发规范 (V2.0)

本规范旨在统一各省份采购公告详情页解析器的开发标准，确保代码的健壮性、可维护性和数据提取的准确性。所有新的解析器或对现有解析器的重构都应遵循此规范。

---

## 一、 文件与类结构

1.  **文件名**: 必须为省份的全拼音小写，例如 `sichuan.py`, `chongqing.py`。
2.  **`BaseParser` 类**: 每个模块必须包含一个 `BaseParser` 基类。**开发者不应修改此基类。**
    ```python
    class BaseParser:
        def parse(self, html: str):
            raise NotImplementedError
    ```
3.  **解析器类**:
    *   必须继承自 `BaseParser`。
    *   命名应能清晰反映其处理的公告类型，例如 `SichuanCentralGovParser` (中央公告), `SichuanLocalGovParser` (地方公告)。
    *   一个文件内可以包含多个解析器类，以应对同一省份下不同的页面结构（如中央公告 vs. 地方公告）。

---

## 二、 `parse` 方法实现规范

`parse` 方法是解析器的核心，负责从给定的 HTML 文本中提取数据。

### 1. 返回值规范

*   `parse` 方法必须返回一个 **列表 (list)**。
*   列表中的每个元素都是一个 **字典 (dict)**，代表一条完整的采购记录。
*   即使页面只包含一条记录，也必须返回包含单个字典的列表，例如 `[{"项目名称": "...", ...}]`。
*   如果页面没有解析到任何有效数据，应返回一个 **空列表 `[]`**。

### 2. 字段规范

每个返回的字典必须包含以下所有字段。如果某个字段在页面上不存在，其值应为字符串 `'N/A'`。

```python
{
    "发布日期": "YYYY-MM-DD",
    "项目号": "...",
    "采购方式": "...",
    "项目名称": "...",
    "供应商名称": "...",
    "中标金额": "...", # 应包含单位，如 '1,024.00元' 或 '123.45万元'
    "名称": "...",
    "品牌": "...",
    "规格型号": "...",
    "数量": "...",
    "单价": "..."
}
```

### 3. 解析策略最佳实践

#### 3.1. 优先使用正则表达式提取非表格数据

对于"项目号"、"项目名称"、"供应商名称"等通常散落在正文段落中的信息，应优先使用正则表达式从整个内容 `div` 的纯文本中提取。这比依赖不稳定的标签（如 `<p>`, `<strong>`）或其顺序更可靠。

**优秀实践**:
```python
# 1. 先获取整个内容容器的纯文本
content_div = soup.select_one('div.vF_detail_content')
content_text = content_div.get_text('\n', strip=True) if content_div else ''

# 2. 使用 re.search 配合捕获组提取信息
project_name_match = re.search(r'二、项目名称[：:\s]*([^\n]+)', content_text)
if project_name_match:
    item['项目名称'] = project_name_match.group(1).strip()
else:
    # 3. 提供备用方案，例如直接使用页面标题
    item['项目名称'] = soup.select_one('h2.tc').get_text(strip=True)
```

#### 3.2. 稳健地定位数据表格

不应依赖表格的 `id` 或 `class`，因为它们易变。最佳实践是先找到一个确定的、不易改变的表头单元格，然后通过它反向查找父级 `<table>` 元素。

**优秀实践**:
```python
# 方法一：通过表头文字定位
main_table = soup.find('td', string=re.compile(r'^\s*货物名称\s*$'))
if main_table:
    main_table = main_table.find_parent('table')

# 方法二：如果方法一失败，通过标题段落定位
if not main_table:
    table_title = soup.find('p', string=re.compile(r'四、主要标的信息'))
    if table_title:
        main_table = table_title.find_next('table')

# 后续在 main_table 的范围内进行解析...
```

#### 3.3. 处理"详见附件"和单元格内换行

*   **直接提取文本**: 如果"规格型号"、"品牌"等字段内明确写着"详见附件"或"见清单"，解析器应**直接提取这些文本**作为字段的值，而不是返回 `N/A`。
*   **处理 `<br>` 换行**: 很多页面使用 `<br>` 在一个 `<td>` 内罗列多个物品。应使用 `.get_text(separator='<br>')` 或 `.stripped_strings` 来处理这种情况。

**优秀实践**:
```python
def parse_multiline_cell(cell):
    """处理一个可能包含 <br> 标签的单元格"""
    if not cell:
        return 'N/A'
    # 使用 .stripped_strings 可以优雅地处理多行和空格
    lines = [line for line in cell.stripped_strings]
    return '；'.join(lines) if lines else 'N/A'

# ... 在表格解析循环中 ...
cols = row.select('td')
if len(cols) > 4:
    item['规格型号'] = parse_multiline_cell(cols[4])
```

#### 3.4. 数据有效性校验

在 `parse` 方法的最后，返回数据前，应进行一次简单的健全性检查，以过滤掉完全无效的空记录。

**优秀实践**:
```python
# 在 return 之前
if item["项目名称"] == "N/A" and item["供应商名称"] == "N/A":
    return [] # 如果关键信息都缺失，则视作无效记录

return [item]
```

---

## 三、 模块级必要函数

每个省份的解析器模块文件都必须提供以下两个与类平级的函数。

### 1. `get_parser_for_url(url: str)`

*   **功能**: 根据传入的 `url`，判断并返回一个最合适的解析器**实例**。
*   **逻辑**: 通常通过 `url` 中包含的特定路径（如 `/zygg/` 或 `/dfgg/`）来判断。
*   **规范**: 如果所有情况都不匹配，必须返回 `None`。

**示例**:
```python
def get_parser_for_url(url: str):
    """根据URL特征返回最合适的解析器实例"""
    if "/dfgg/" in url:
        return ChongqingLocalGovParser()
    elif "/zygg/" in url:
        return ChongqingCentralGovParser()
    return None
```

### 2. `get_dynamic_html(url: str)`

*   **功能**: 使用 `Selenium` 获取指定 `url` 的动态渲染后的 HTML 内容。
*   **规范**:
    *   必须使用 `headless` 无头模式。
    *   必须包含异常处理（如 `TimeoutException`），在加载失败时应打印日志并返回 `None`。
    *   必须在 `finally` 块中调用 `driver.quit()` 以确保浏览器进程被关闭。
    *   推荐使用 `webdriver_manager` 自动管理 `ChromeDriver`。

**示例**:
```python
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def get_dynamic_html(url: str) -> str:
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    # ... 其他推荐选项 ...
    
    driver = None
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        # 等待一个页面加载完成的关键元素
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.vF_detail_content"))
        )
        return driver.page_source
    except TimeoutException:
        print(f"页面加载超时: {url}")
        return None
    except Exception as e:
        print(f"获取动态HTML时发生错误: {e}")
        return None
    finally:
        if driver:
            driver.quit()
``` 