# simulate_search_gui.py

import time
import pandas as pd
from datetime import datetime
from bs4 import BeautifulSoup
from tkinter import Tk, Label, Entry, Button, StringVar
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from url_builder import build_ccgp_search_url
from detail_parsers import PARSER_MAP


def get_search_results(driver):
    """从当前页面提取公告列表"""
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "ul.vT-srch-result-list > li"))
        )
    except:
        print("⚠️ 页面加载超时，无搜索结果")
        return []

    soup = BeautifulSoup(driver.page_source, "html.parser")
    items = soup.select("ul.vT-srch-result-list > li")
    results = []
    for li in items:
        title = li.find("a").get_text(strip=True)
        href = li.find("a")["href"]
        link = href if href.startswith("http") else "https://www.ccgp.gov.cn" + href
        date = li.find("span").get_text(strip=True)
        results.append({
            "标题": title,
            "链接": link,
            "发布日期": date
        })
    return results


def extract_detail(driver, result, province):
    parser_class = PARSER_MAP.get(province)
    if not parser_class:
        print(f"❌ 缺少 {province} 的解析器")
        return None
    parser = parser_class()
    try:
        driver.get(result["链接"])
        time.sleep(2)
        html = driver.page_source
        data = parser.parse(html)
        data.update(result)
        data["省份"] = province
        return data
    except Exception as e:
        print(f"⚠️ 解析失败: {e}")
        return None


def start_crawl(province, start_date, end_date):
    keyword = "空调"
    chrome_options = Options()
    # 可视化运行以便调试，不使用 headless
    # chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options)

    all_data = []
    page = 1

    while True:
        url = build_ccgp_search_url(province, start_date, end_date, keyword, page)
        print(f"\n📄 第 {page} 页：{url}")
        driver.get(url)
        time.sleep(2)

        page_results = get_search_results(driver)
        if not page_results:
            print("📭 无结果，结束抓取")
            break

        for i, result in enumerate(page_results, 1):
            print(f"🔎 [{i}/{len(page_results)}]：{result['标题']}")
            detail = extract_detail(driver, result, province)
            if detail:
                all_data.append(detail)

        # 判断是否存在“下一页”
        try:
            driver.find_element(By.LINK_TEXT, "下一页")
            page += 1
        except:
            print("✅ 没有更多页面")
            break

    driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        filename = f"output/中标公告_空调_{province}_{start_date}_to_{end_date}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ 成功抓取 {len(all_data)} 条，文件已保存：{filename}")
    else:
        print("❌ 没有成功提取任何数据")


def launch_gui():
    # 创建窗口
    root = Tk()
    root.title("政府采购爬虫")
    root.geometry("400x200")

    province_var = StringVar()
    start_var = StringVar()
    end_var = StringVar()

    Label(root, text="省份（如：江苏）").pack()
    Entry(root, textvariable=province_var).pack()

    Label(root, text="开始日期（YYYY-MM-DD）").pack()
    Entry(root, textvariable=start_var).pack()

    Label(root, text="结束日期（YYYY-MM-DD）").pack()
    Entry(root, textvariable=end_var).pack()

    def run():
        province = province_var.get().strip()
        start = start_var.get().strip()
        end = end_var.get().strip()
        root.destroy()
        start_crawl(province, start, end)

    Button(root, text="开始爬取", command=run).pack(pady=10)
    root.mainloop()


if __name__ == "__main__":
    launch_gui()
