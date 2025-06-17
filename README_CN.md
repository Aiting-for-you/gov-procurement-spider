# 中国政府采购网数据采集器

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI Framework](https://img.shields.io/badge/UI-CustomTkinter-blue)](https://github.com/TomSchimansky/CustomTkinter)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个功能强大、模块化且用户友好的网络爬虫工具，专为提取和解析中国政府采购网 (ccgp.gov.cn) 的公开采购公告而设计。本项目提供了一个健壮、可扩展的后端和一个直观的图形界面，让您能轻松地从不同省份采集结构化数据。

---

## 📖 目录

- [核心功能](#-核心功能)
- [技术栈](#-技术栈)
- [项目结构](#-项目结构)
- [安装指南](#-安装指南)
- [如何使用](#-如何使用)
- [如何贡献](#-如何贡献)
- [许可协议](#-许可协议)
- [免责声明](#-免责声明)

---

## ✨ 核心功能

- **直观的图形用户界面 (GUI)**: 基于 `CustomTkinter` 构建的简洁图形界面，让用户可以：
  - 从下拉菜单中选择省份。
  - 输入指定的搜索关键词。
  - 使用日历控件选择日期范围。
  - 在应用内直接查看实时日志。
  - 一键将所有抓取到的 CSV 文件合并转换为单个 Excel 文件。
- **模块化与可扩展架构**: 每个省份的解析器都是一个独立的模块，便于新增、维护和调试。项目提供清晰的规范文档 (`parser_module_specification.md`) 以供参考。
- **强大的采集引擎**: 利用 `Selenium` 处理动态网页，并结合 `BeautifulSoup` 进行高效的 HTML 解析，确保在不同页面结构下的可靠性。
- **自动化测试套件**: 包含一个批量测试脚本 (`batch_test.py`)，用于验证所有省份解析器的功能，确保代码的稳定性和质量。
- **灵活的数据导出**: 将抓取的数据保存为结构化的 `.csv` 文件，并内置一个转换工具，可将它们合并为单个、规整的 `.xlsx` 文件。
- **集中化配置**: 省份映射关系在单一文件 (`province_mapping.py`) 中管理，简化了添加或移除省份的流程。

---

## 🛠️ 技术栈

- **后端**: Python 3.9+
- **网络爬虫**: Selenium, BeautifulSoup4
- **图形界面**: CustomTkinter, Tkinter
- **数据处理**: Pandas
- **打包工具**: PyInstaller

---

## 📁 项目结构

```
gov-procurement-spider/
│
├── detail_parsers/         # 存放各个省份的独立解析器模块
├── output/                 # 默认用于存放输出的 CSV 和 Excel 文件
│
├── .gitignore              # 指定 Git 应忽略的文件
├── batch_test.py           # 用于自动化测试所有省份解析器的脚本
├── config.py               # 配置文件 (例如超时设置)
├── converter.py            # 用于将 CSV 文件转换为单个 Excel 文件的脚本
├── gui_app.py              # GUI 应用的主文件
├── LICENSE                 # 项目的 MIT 许可协议文件
├── logger_config.py        # 日志记录的配置文件
├── main.py                 # 命令行界面的主脚本
├── province_mapping.py     # 集中管理省份中文名与解析器模块的映射关系
├── README.md               # 英文版 README 文件
├── README_CN.md            # 中文版 README 文件
├── report_generator.py     # (未来使用) 用于生成格式化报告
├── requirements.txt        # 项目的所有 Python 依赖项列表
├── search_parser.py        # 用于解析搜索结果列表页的解析器
└── url_builder.py          # 用于构建搜索 URL
```

---

## ⚙️ 安装指南

### 环境要求

- Python 3.9 或更高版本
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
    python -m venv venv
    venv\Scripts\activate

    # macOS & Linux 系统
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **安装所需依赖:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚀 如何使用

本应用可以通过图形用户界面 (推荐) 或命令行两种方式运行。

### 1. 使用图形用户界面 (GUI)

通过运行以下命令启动应用:
```bash
python gui_app.py
```

**操作流程:**
1.  **选择省份**: 从下拉菜单中选择一个省份。
2.  **输入关键词**: 输入您感兴趣的搜索词。
3.  **设置日期范围**: 使用日历控件定义开始和结束日期。
4.  **选择输出目录**: 点击按钮选择文件保存位置 (默认为 `output/`)。
5.  **开始采集**: 点击"开始爬取"按钮启动任务。
6.  **监控进度**: 在日志窗口查看实时更新。
7.  **转换为 Excel**: 采集完成后，点击"将结果转为Excel"，即可生成单个 `.xlsx` 文件。

### 2. 使用命令行界面 (CLI)

对于高级用户或自动化场景，您可以使用命令行。
```bash
python main.py
```
脚本将提示您依次输入省份、关键词、开始日期和结束日期。

---

## 🤝 如何贡献

欢迎任何形式的贡献！如果您希望改进此工具或添加新功能，请遵循以下步骤。

### 添加新的省份解析器

1.  **创建解析器文件**: 在 `detail_parsers/` 目录下创建一个新的 Python 文件 (例如 `hainan.py`)。
2.  **实现解析器类**: 在新文件中，创建一个继承自 `BaseParser` 的类，并实现 `parse(self, html: str)` 方法。您可以参考现有解析器作为示例，并遵循 `parser_module_specification.md` 中的指导。
3.  **更新省份映射**: 打开 `province_mapping.py` 文件，在 `PROVINCE_PINYIN_MAP` 字典中添加新省份的中文名及其对应的拼音名称。
4.  **添加测试用例**: 打开 `batch_test.py` 文件，在 `TEST_CASES` 字典中为您的新省份添加一个测试 URL。
5.  **运行测试**: 执行批量测试脚本，以确保您的新解析器能够正常工作，并且没有破坏任何现有功能。
    ```bash
    python batch_test.py
    ```
6.  **提交合并请求 (Pull Request)**: 当所有测试通过后，提交您的更改并发起一个合并请求！

---

## 📜 许可协议

本项目采用 MIT 许可协议。详情请参阅 [LICENSE](LICENSE) 文件。

---

## ⚖️ 免责声明

本工具仅供教育和研究目的使用。所有数据均从公开的政府网站抓取，其准确性完全取决于数据源。本工具的开发者对任何不当使用本软件的行为不承担责任。请负责任地使用本工具，并遵守 ccgp.gov.cn 的服务条款。