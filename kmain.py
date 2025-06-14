# main.py

import argparse
import time
import pandas as pd
from datetime import datetime

from simulate_search import simulate_search
from detail_parsers import PARSER_MAP
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def extract_details(results, province):
    """处理每个详情页，使用对应省份解析器提取字段"""
    all_data = []
    parser_class = PARSER_MAP.get(province)
    if not parser_class:
        print(f"❌ 暂无 {province} 的解析器")
        return []

    parser = parser_class()

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options)

    for i, item in enumerate(results, 1):
        print(f"🔎 正在处理第 {i} 条：{item['标题']}")
        try:
            driver.get(item["链接"])
            time.sleep(2)
            html = driver.page_source
            data = parser.parse(html)
            data.update({
                "标题": item["标题"],
                "链接": item["链接"],
                "发布日期": item["发布日期"],
                "省份": province
            })
            all_data.append(data)
        except Exception as e:
            print(f"❗ 解析失败：{e}，链接：{item['链接']}")
            continue

    driver.quit()
    return all_data

def save_to_csv(data, keyword, province, start_date, end_date):
    """保存为 CSV 文件"""
    df = pd.DataFrame(data)
    filename = f"output/中标公告_{keyword}_{province}_{start_date}_to_{end_date}.csv"
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"\n✅ 数据已保存：{filename}")

def main():
    parser = argparse.ArgumentParser(description="中国政府采购网爬虫")
    parser.add_argument("--province", required=True, help="省份（如：江苏）")
    parser.add_argument("--keyword", default="空调", help="关键词")
    parser.add_argument("--start", required=True, help="开始日期（YYYY-MM-DD）")
    parser.add_argument("--end", required=True, help="结束日期（YYYY-MM-DD）")
    parser.add_argument("--pages", type=int, default=3, help="最大页数")

    args = parser.parse_args()

    province = args.province
    keyword = args.keyword
    start_date = args.start
    end_date = args.end
    max_pages = args.pages

    print(f"\n📍 省份：{province}")
    print(f"🔍 关键词：{keyword}")
    print(f"📅 时间范围：{start_date} ~ {end_date}")
    print(f"📄 抓取页数：{max_pages}")

    print("\n🧭 开始模拟筛选并获取搜索结果...")
    search_results = simulate_search(keyword, start_date, end_date, province, max_pages=max_pages)

    if not search_results:
        print("❌ 未获取到搜索结果")
        return

    print(f"\n📦 共获取到 {len(search_results)} 条搜索结果，开始提取详情页内容...")
    all_data = extract_details(search_results, province)

    if all_data:
        save_to_csv(all_data, keyword, province, start_date, end_date)
    else:
        print("❌ 无有效数据提取")

if __name__ == "__main__":
    main()
