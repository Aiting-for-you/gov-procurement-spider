# China Government Procurement Spider

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![UI Framework](https://img.shields.io/badge/UI-CustomTkinter-blue)](https://github.com/TomSchimansky/CustomTkinter)

A sophisticated and modular web scraping solution for extracting and parsing public procurement announcements from China's official government procurement website (ccgp.gov.cn). This tool features a user-friendly graphical interface and a robust, extensible backend, making it easy to gather structured data across various provinces.

---

## 🌟 Project Status

**This project is under active development.** New parsers for additional provinces are being added, and existing ones are continuously improved for better accuracy and resilience. Contributions are welcome!

---

## ✨ Features

- **User-Friendly GUI**: An intuitive graphical interface built with `CustomTkinter` that allows you to:
    - Select provinces from a dropdown menu.
    - Freely enter any search keywords.
    - Choose date ranges with a calendar.
    - View real-time logs directly in the app.
- **Multi-Province Support**: Comes with dedicated parsers for multiple provinces. The current supported list includes:
    > Anhui, Chongqing, Guangdong, Guangxi, Hebei, Hubei, Jiangsu, Shandong, Sichuan, Zhejiang
- **Modular Architecture**: Each province's parser is a self-contained module, making it easy to extend, maintain, and debug.
- **Robust Parsing Engine**: Utilizes `Selenium` and `BeautifulSoup` to handle complex, dynamic, and varied page structures.
- **Data Export**: Saves extracted data into structured `.csv` files, ready for analysis.
- **Extensible**: Includes a clear specification (`parser_module_specification.md`) for creating new parser modules.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Google Chrome browser installed

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Aiting-for-you/gov-procurement-spider.git
    cd gov-procurement-spider
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    # On Windows
    python -m venv venv && venv\Scripts\activate
    # On macOS/Linux
    python -m venv venv && source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🛠️ Usage

### 1. Graphical User Interface (Recommended)

The easiest way to use the spider is through the GUI.

**Launch the application:**
```bash
python gui_app.py
```

**How to use:**
1.  Select a province from the dropdown menu.
2.  Enter your desired search keyword.
3.  Set the start and end dates using the calendar widgets.
4.  Click the "Start Crawling" button.
5.  Monitor the progress in the log window.
6.  Find the results in the `output/` directory upon completion.

### 2. Command-Line Interface (for advanced users)

You can also run the spider directly from the command line.

**Launch the CLI:**
```bash
python main.py
```
The script will then prompt you to enter the province (in Chinese), keyword, start date, and end date.

---

## 🔧 How to Extend with a New Province Parser

To add support for a new province, follow these steps:

1.  **Create a new Python file** in the `detail_parsers/` directory (e.g., `new_province.py`).
2.  **Implement a parser class** that inherits from `BaseParser` and implements the `parse(self, html: str)` method, following the logic in `parser_module_specification.md`.
3.  **Update the province map** in `gui_app.py` and `main.py` to include the Chinese name and pinyin of the new province.
4.  That's it! The GUI and CLI will automatically detect the new parser file and add it to the selection list.

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

-   **Reporting Issues**: If you find a bug or have a suggestion, please open an issue.
-   **Adding Parsers**: The most valuable way to contribute is by adding a new parser for a province not yet supported.
-   **Pull Requests**: Feel free to fork the repo and submit a pull request for any improvements.

---

## 📜 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## ⚖️ Disclaimer

This tool is intended for educational and research purposes only. The data is scraped from public government websites, and its accuracy depends on the source. Please use this tool responsibly and in accordance with the terms of service of ccgp.gov.cn. The developers are not responsible for any misuse of this software.
