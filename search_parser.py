# 搜索结果页爬取模块
# search_parser.py

from bs4 import BeautifulSoup
import time

def parse_search_results(driver, url, max_pages=50):
    """抓取搜索页中的所有公告链接与基本信息"""
    results = []
    for page in range(1, max_pages + 1):
        page_url = url.format(page=page)
        driver.get(page_url)
        time.sleep(2)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.select("ul.vT-srch-result-list > li")
        if not items:
            break

        for li in items:
            title = li.find("a").get_text(strip=True)
            href = li.find("a")["href"]
            date_text = li.find("span").get_text(strip=True)
            full_url = href if href.startswith("http") else "https://www.ccgp.gov.cn" + href
            results.append({
                "标题": title,
                "链接": full_url,
                "发布日期": date_text
            })

    return results
