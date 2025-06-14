# 中国政府采购网爬虫

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI Framework](https://img.shields.io/badge/UI-CustomTkinter-blue)](https://github.com/TomSchimansky/CustomTkinter)

一个功能强大且模块化的网络爬虫，专为提取和解析中国政府采购网 (ccgp.gov.cn) 的公开采购公告而设计。本项目提供了一个用户友好的图形界面和一个健壮、可扩展的后端，让您能轻松地从不同省份采集结构化数据。

---

## 🌟 项目状态

**本项目正处于活跃开发阶段。** 我们正在不断为新的省份添加解析器，并持续优化现有解析器的准确性和稳定性。欢迎大家参与贡献！

---

## ✨ 项目特性

- **友好的图形用户界面 (GUI)**: 基于 `CustomTkinter` 构建的直观图形界面，让您可以：
    - 从下拉菜单中选择省份。
    - 自由输入任意搜索关键词。
    - 使用日历控件选择日期范围。
    - 在应用内直接查看实时日志。
- **多省份支持**: 内置了针对多个省份的专用解析器。当前已支持的省份列表包括：
    > 安徽、重庆、广东、广西、河北、湖北、江苏、山东、四川、浙江
- **模块化架构**: 每个省份的解析器都是一个独立的模块，易于扩展、维护和调试。
- **强大的解析引擎**: 使用 `Selenium` 和 `BeautifulSoup` 处理复杂、动态和多样的页面结构。
- **数据导出**: 将提取的数据保存为结构化的 `.csv` 文件，便于后续分析。
- **易于扩展**: 项目包含了清晰的规范文档 (`parser_module_specification.md`)，用于指导如何为新的省份创建解析器模块。

---

## 💾 下载

最简单的使用方式是直接从 **[Releases](https://github.com/Aiting-for-you/gov-procurement-spider/releases)** 页面下载最新版本。

1.  访问 [Releases](https://github.com/Aiting-for-you/gov-procurement-spider/releases) 页面。
2.  从最新版本中下载 `GovSpider.zip` 文件。
3.  解压缩该文件。
4.  双击 `政府采购爬虫.exe` 即可运行。

---

## 🚀 快速开始 (面向开发者)

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
    # Windows 系统
    python -m venv venv && venv\Scripts\activate
    # macOS/Linux 系统
    python -m venv venv && source venv/bin/activate
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🛠️ 如何使用

### 1. 图形用户界面 (推荐)

使用图形界面是运行本爬虫最简单的方式。

**启动应用:**
```bash
python gui_app.py
```

**使用方法:**
1.  从下拉菜单中选择一个省份。
2.  输入您想查询的关键词。
3.  使用日历控件设置开始和结束日期。
4.  点击"开始爬取"按钮。
5.  在日志窗口中监控进度。
6.  任务完成后，在 `output/` 目录中找到结果文件。

### 2. 将 CSV 转换为 Excel

运行爬虫后，您可以将生成的 `.csv` 文件转换为更便于使用的 Excel (`.xlsx`) 格式。

**运行转换器:**
```bash
python converter.py
```
该脚本将自动扫描 `output/` 目录，并将所有存在的 `.csv` 文件转换为 `.xlsx` 文件。

### 3. 命令行界面 (高级用户)

您也可以直接通过命令行来运行爬虫。

**启动命令行:**
```bash
python main.py
```
脚本将提示您依次输入省份（中文）、关键词、开始日期和结束日期。

---

## 🔧 如何扩展新的省份解析器

要为新的省份添加支持，请遵循以下步骤:

1.  在 `detail_parsers/` 目录下**创建一个新的Python文件** (例如, `new_province.py`)。
2.  **实现一个继承自 `BaseParser` 的解析器类**，并实现 `parse(self, html: str)` 方法。请遵循 `parser_module_specification.md` 中概述的逻辑。
3.  在 `gui_app.py` 和 `main.py` 的**省份映射字典中**加入新省份的中文名和拼音。
4.  完成！图形界面和命令行将自动检测到新的解析器文件并将其加入到选项中。

---

## 🤝 如何贡献

开源社区因贡献而充满活力。我们**非常感谢**您对本项目的任何贡献。

-   **报告问题**: 如果您发现任何错误或有改进建议，请提交一个 Issue。
-   **添加解析器**: 最有价值的贡献方式是为尚未支持的省份添加新的解析器。
-   **提交拉取请求 (Pull Request)**: 欢迎您 Fork 本项目，并为任何改进提交拉取请求。

---

## 📜 许可协议

本项目采用 MIT 许可协议。详情请参阅 [LICENSE](LICENSE) 文件。

---

## ⚖️ 免责声明

本工具仅供教育和研究目的使用。所有数据均从公开的政府网站抓取，其准确性取决于数据源。请负责任地使用本工具，并遵守 ccgp.gov.cn 的服务条款。开发者对任何不当使用本软件的行为不承担责任。
