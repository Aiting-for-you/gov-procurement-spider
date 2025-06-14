# 中国政府采购网爬虫

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

一个功能强大且模块化的网络爬虫，专为提取和解析中国政府采购网 (ccgp.gov.cn) 的公开采购公告而设计。该工具能够处理不同省份复杂、动态和多样的页面结构，并提供结构化的公告数据。

---

## 🌟 项目状态

**本项目正处于活跃开发阶段。** 我们正在不断为新的省份添加解析器，并持续优化现有解析器的准确性和稳定性。欢迎大家参与贡献！

---

## ✨ 项目特性

- **多省份支持**: 内置了针对多个省份的专用解析器，包括广东、浙江、山东、四川、河北等。
- **模块化架构**: 每个省份的解析器都是一个独立的模块，易于扩展、维护和调试。一个中央工厂函数会根据公告URL自动选择正确的解析器。
- **强大的解析引擎**:
    - 使用 `Selenium` 处理动态加载的JavaScript内容，确保捕获所有数据。
    - 使用 `BeautifulSoup` 和 `lxml` 进行高效、容错的HTML解析。
    - 智能处理各种复杂的页面布局，例如：
        - 包含多个标包的中标公告。
        - 单元格内含多行文本的表格 (处理 `<br>` 标签)。
        - 由各种分隔符分割的非表格化数据。
        - 中央和地方公告之间不一致的HTML结构。
- **动态与智能**: 能够在同一个省份的模块内，自动适应不同的页面结构（例如，单包件与多包件中标）。
- **数据导出**: 主程序 (`main.py`) 的逻辑设计为将提取的数据保存为结构化的 `.csv` 文件。
- **易于扩展**: 项目包含了清晰的规范文档 (`parser_module_specification.md`)，用于指导如何为新的省份创建解析器模块。

---

## 🚀 快速开始

### 环境要求

- Python 3.9+
- 已安装 Google Chrome 浏览器

### 安装步骤

1.  **克隆代码仓库:**
    ```bash
    git clone https://github.com/Aiting-for-you/gov-procurement-spider.git
    cd gov-procurement-spider
    ```

2.  **创建并激活虚拟环境 (推荐):**
    ```bash
    python -m venv venv
    # Windows 系统
    venv\Scripts\activate
    # macOS/Linux 系统
    source venv/bin/activate
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🛠️ 如何使用

项目的主入口点是 `main.py`。其主要工作流程如下:
1.  为不同省份和关键词（如 "空调"）构建一个搜索URL列表。
2.  爬取搜索结果页面，以查找具体公告详情页的链接。
3.  为每个详情页链接，动态选择合适的省级解析器。
4.  解析页面，提取结构化数据。
5.  将结果保存到 `output/` 目录下的 `.csv` 文件中。

要运行爬虫，只需执行 `main.py` 脚本:
```bash
python main.py
```
运行结束后，请在 `output/` 文件夹中查看生成的CSV文件。

---

## 🔧 如何扩展新的省份解析器

要为新的省份添加支持，请遵循以下步骤:

1.  在 `detail_parsers/` 目录下**创建一个新的Python文件** (例如, `new_province.py`)。
2.  在该文件中，**实现一个继承自 `BaseParser` 的解析器类**，并实现 `parse(self, html: str)` 方法。
3.  **遵循 `parser_module_specification.md` 中概述的逻辑**。你的解析器需要能够处理新省份公告的特定HTML结构。可以参考现有的解析器 (如 `sichuan.py` 或 `hebei.py`) 来处理复杂情况。
4.  在你的新文件中**添加一个工厂函数** `get_parser_for_url(url: str)`。此函数将实例化并返回你的新解析器。
5.  **更新 `main.py` 中的主工厂函数**以包含你的新省份。添加一个 `elif` 条件来检查省份的URL模式，并导入你的新 `get_parser_for_url` 函数。

```python
# 在 main.py 的 get_detail_parser 函数中

# ... 已有代码 ...
elif 'sichuan' in province_identifier: # 示例
    from detail_parsers.sichuan import get_parser_for_url
    return get_parser_for_url(url)
elif 'new_province' in province_identifier: # 在此处添加你的新省份
    from detail_parsers.new_province import get_parser_for_url
    return get_parser_for_url(url)
# ...
``` 

---

## 🤝 如何贡献

开源社区因贡献而充满活力。我们**非常感谢**您对本项目的任何贡献。

-   **报告问题**: 如果您发现任何错误或有改进建议，请提交一个 Issue。
-   **添加解析器**: 最有价值的贡献方式是为尚未支持的省份添加新的解析器。请遵循 `parser_module_specification.md` 指南。
-   **提交拉取请求 (Pull Request)**: 欢迎您 Fork 本项目，并为任何改进提交拉取请求。

---

## 📜 许可协议

本项目采用 MIT 许可协议。详情请参阅 [LICENSE](LICENSE) 文件。

---

## ⚖️ 免责声明

本工具仅供教育和研究目的使用。所有数据均从公开的政府网站抓取，其准确性取决于数据源。请负责任地使用本工具，并遵守 ccgp.gov.cn 的服务条款。开发者对任何不当使用本软件的行为不承担责任。
