# China Government Procurement Data Scraper

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI Framework](https://img.shields.io/badge/UI-CustomTkinter-blue)](https://github.com/TomSchimansky/CustomTkinter)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful, modular, and user-friendly web scraping tool designed to extract and parse public procurement announcements from China's official government procurement website (ccgp.gov.cn). It features a robust, extensible backend and an intuitive graphical interface, making it easy to gather structured data across various provinces.

---

## 📖 Table of Contents

- [Core Features](#-core-features)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Installation Guide](#-installation-guide)
- [How to Use](#-how-to-use)
- [How to Contribute](#-how-to-contribute)
- [License](#-license)
- [Disclaimer](#-disclaimer)

---

## ✨ Core Features

- **Intuitive GUI**: A clean graphical interface built with `CustomTkinter` that allows users to:
  - Select a province from a dropdown menu.
  - Specify search keywords.
  - Select a date range using calendar widgets.
  - View real-time logs directly within the application.
  - Convert all scraped CSV files to a single Excel file with one click.
- **Modular & Extensible Architecture**: Each province's parser is a self-contained module, making it easy to add new provinces, perform maintenance, and debug. A clear specification (`parser_module_specification.md`) is provided for guidance.
- **Robust Scraping Engine**: Utilizes `Selenium` to handle dynamic web pages and `BeautifulSoup` for efficient HTML parsing, ensuring reliability across varied page structures.
- **Automated Testing Suite**: Includes a batch testing script (`batch_test.py`) to verify the functionality of all provincial parsers, ensuring stability and code quality.
- **Flexible Data Export**: Saves extracted data into structured `.csv` files and includes a built-in converter to merge them into a single, organized `.xlsx` file.
- **Centralized Configuration**: Province mappings are managed in a single file (`province_mapping.py`), simplifying the process of adding or removing provinces.

---

## 🛠️ Tech Stack

- **Backend**: Python 3.9+
- **Scraping**: Selenium with local ChromeDriver, BeautifulSoup4
- **GUI**: CustomTkinter, Tkinter
- **Data Handling**: Pandas
- **Packaging**: PyInstaller
- **Browser Engine**: Local ChromeDriver (included in executable version)

---

## 📁 Project Structure

```
gov-procurement-spider/
│
├── detail_parsers/         # Contains individual parser modules for each province.
├── output/                 # Default directory for storing output CSV and Excel files.
│
├── .gitignore              # Specifies files to be ignored by Git.
├── batch_test.py           # Script to test all province parsers automatically.
├── config.py               # Configuration settings (e.g., timeouts).
├── converter.py            # Script to convert CSV files to a single Excel file.
├── gui_app.py              # Main application file for the GUI.
├── LICENSE                 # Project's MIT License file.
├── logger_config.py        # Configuration for logging.
├── main.py                 # Main script for the command-line interface.
├── province_mapping.py     # Central mapping of province names to parser modules.
├── README.md               # English README file.
├── README_CN.md            # Chinese README file.
├── report_generator.py     # (Future Use) For generating formatted reports.
├── requirements.txt        # Lists all Python dependencies for the project.
├── search_parser.py        # Parser for the search results list pages.
└── url_builder.py          # Constructs the search URLs.
```

---

## ⚙️ Installation Guide

### Option 1: Ready-to-Use Executable (Recommended for Non-Developers)

**For users who want to use the tool without setting up a development environment:**

1. Download the latest release package containing the executable file
2. Extract the compressed file to your desired location
3. Run the `.exe` file directly - no additional setup required!
4. The executable includes all necessary dependencies and ChromeDriver

### Option 2: Development Setup

**For developers or users who want to run from source code:**

#### Prerequisites

- Python 3.9 or newer
- Google Chrome browser installed
- **Note**: This version uses a local ChromeDriver for enhanced compatibility

#### Setup Steps

1.  **Clone the repository:**
    ```bash
    git clone https://gitee.com/into-the-desert/gov_procurement_spider.git
    cd gov-procurement-spider
    ```

    **Branch Selection:**
    - **Current branch (master)**: Uses local ChromeDriver for enhanced compatibility
    - **Alternative branch**: If you prefer not to use the local ChromeDriver version, you can switch to the `no-local-chromedriver` branch:
      ```bash
      git checkout no-local-chromedriver
      ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    # On Windows
    python -m venv venv
    venv\Scripts\activate

    # On macOS & Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🚀 How to Use

The application can be run via the graphical user interface (recommended) or the command line.

### 1. Using the GUI

Launch the application by running:
```bash
python gui_app.py
```

**Workflow:**
1.  **Select Province**: Choose a province from the dropdown menu.
2.  **Enter Keyword**: Type the search term you are interested in.
3.  **Set Date Range**: Use the calendar widgets to define the start and end dates.
4.  **Choose Output Directory**: Click the button to select where you want to save the files (defaults to `output/`).
5.  **Start Crawling**: Click the "Start Crawling" button to begin the process.
6.  **Monitor Progress**: Watch the log window for real-time updates.
7.  **Convert to Excel**: After crawling is complete, click "Convert Results to Excel" to generate a single `.xlsx` file.

### 2. Using the Command-Line Interface (CLI)

For advanced users or automated workflows, you can use the CLI.
```bash
python main.py
```
The script will prompt you to enter the province, keyword, start date, and end date.

---

## 🤝 How to Contribute

Contributions are welcome! If you'd like to improve the tool or add a new feature, please follow these steps.

### Adding a New Province Parser

1.  **Create Parser File**: Create a new Python file in the `detail_parsers/` directory (e.g., `hainan.py`).
2.  **Implement Parser Class**: Inside the new file, create a class that inherits from `BaseParser` and implements the `parse(self, html: str)` method. Refer to existing parsers for examples and `parser_module_specification.md` for guidelines.
3.  **Update Province Map**: Open `province_mapping.py` and add the new province's Chinese name and its corresponding pinyin name to the `PROVINCE_PINYIN_MAP` dictionary.
4.  **Add a Test Case**: Open `batch_test.py` and add a test URL for your new province to the `TEST_CASES` dictionary.
5.  **Run Tests**: Execute the batch test script to ensure your new parser works correctly and doesn't break existing ones.
    ```bash
    python batch_test.py
    ```
6.  **Submit a Pull Request**: Once all tests pass, commit your changes and open a pull request!

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.

---

## ⚖️ Disclaimer

This tool is intended for educational and research purposes only. All data is scraped from public government websites, and its accuracy depends entirely on the source. The developers of this tool are not responsible for any misuse of the software. Please use this tool responsibly and in accordance with the terms of service of ccgp.gov.cn.