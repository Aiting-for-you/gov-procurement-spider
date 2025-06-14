# China Government Procurement Spider

A sophisticated and modular web scraping solution designed to extract and parse public procurement announcements from the official Chinese Government Procurement website (ccgp.gov.cn). This tool is built to handle complex, dynamic, and varied page structures across different provinces, providing structured data from announcements.

---

## ✨ Features

- **Multi-Province Support**: Comes with dedicated parsers for multiple provinces including Guangdong, Zhejiang, Shandong, Sichuan, Hebei, and more.
- **Modular Architecture**: Each province's parser is a self-contained module, making it easy to extend, maintain, and debug. A central factory automatically selects the correct parser based on the announcement URL.
- **Robust Parsing Engine**:
    - Utilizes `Selenium` to handle dynamically loaded JavaScript content, ensuring all data is captured.
    - Employs `BeautifulSoup` with `lxml` for efficient and resilient HTML parsing.
    - Intelligently handles_ various complex layouts, such as:
        - Announcements with multiple bid packages.
        - Tables with multi-line cells (`<br>` tags).
        - Non-tabular data separated by various delimiters.
        - Inconsistent HTML structures between central and local government announcements.
- **Dynamic & Smart**: Automatically adapts to different page structures (e.g., single vs. multi-package bids) within the same province module.
- **Data Export**: The main application logic (in `main.py`) is designed to save the extracted data into structured `.csv` files.
- **Extensible**: Includes a clear specification (`parser_module_specification.md`) for creating new parser modules for additional provinces.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Google Chrome browser installed

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd gov_procurement_spider
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## 🛠️ Usage

The main entry point for running the spider is `main.py`. It is configured to:
1.  Build a list of search URLs for different provinces and keywords (e.g., "空调" - air conditioner).
2.  Scrape the search result pages to find links to individual announcement detail pages.
3.  For each detail page, dynamically select the appropriate provincial parser.
4.  Parse the page to extract structured data.
5.  Save the results into a `.csv` file in the `output/` directory.

To run the spider, simply execute the `main.py` script:
```bash
python main.py
```
Check the `output/` folder for the resulting CSV files.

---

## 🔧 How to Extend with a New Province Parser

To add support for a new province, follow these steps:

1.  **Create a new Python file** in the `detail_parsers/` directory (e.g., `new_province.py`).
2.  **Implement a parser class** inside this file that inherits from `BaseParser` and implements the `parse(self, html: str)` method.
3.  **Follow the logic outlined in `parser_module_specification.md`**. Your parser should handle the specific HTML structure of the new province's announcements. Use existing parsers (like `sichuan.py` or `hebei.py`) as a reference for handling complex cases.
4.  **Add a factory function** `get_parser_for_url(url: str)` in your new file. This function will instantiate and return your new parser.
5.  **Update the main factory** in `main.py` to include your new province. Add an `elif` condition to check for the province's URL pattern and import your new `get_parser_for_url` function.

```python
# In main.py, inside the get_detail_parser function

# ... existing code ...
elif 'sichuan' in province_identifier: # Example
    from detail_parsers.sichuan import get_parser_for_url
    return get_parser_for_url(url)
elif 'new_province' in province_identifier: # Add your new province here
    from detail_parsers.new_province import get_parser_for_url
    return get_parser_for_url(url)
# ...
``` 