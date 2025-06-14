# main.py

import time
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import importlib

from url_builder import build_ccgp_search_url


def get_project_links_from_page(driver):
    """从当前页面获取项目链接"""
    project_links = []

    try:
        wait = WebDriverWait(driver, 10)

        print(f"页面标题: {driver.title}")
        print(f"当前URL: {driver.current_url}")

        try:
            result_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".vT-srch-result-list-bid"))
            )
            print("找到搜索结果容器")
            link_elements = result_container.find_elements(By.CSS_SELECTOR, "li a[href]")
            print(f"在结果容器中找到 {len(link_elements)} 个链接")

            for element in link_elements:
                href = element.get_attribute("href")
                if href and ("ccgp.gov.cn" in href and (".htm" in href or "detail" in href)):
                    project_links.append(href)
                    print(f"添加项目链接: {href[:80]}...")

        except TimeoutException:
            print("未找到搜索结果容器，尝试其他方法")
            selectors = [
                "a[style='line-height:18px']",
                ".vT-srch-result-list-bid a",
                "a[href*='ccgp.gov.cn'][href*='.htm']",
                "a[href*='cggg']",
                ".vT-srch-result a",
                "li a[href]",
                "a[title]"
            ]

            for selector in selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        print(f"使用选择器 '{selector}' 找到 {len(elements)} 个链接")
                        for element in elements:
                            href = element.get_attribute("href")
                            if href and "ccgp.gov.cn" in href and (".htm" in href or "detail" in href):
                                project_links.append(href)
                                print(f"添加链接: {href[:80]}...")
                        if project_links:
                            print(f"成功获取到 {len(project_links)} 个项目链接")
                            break
                except Exception as e:
                    print(f"选择器 '{selector}' 失败: {e}")
                    continue

    except Exception as e:
        print(f"获取项目链接时出错: {e}")

    unique_links = list(set(project_links))
    print(f"总共找到 {len(unique_links)} 个唯一项目链接")

    if not unique_links:
        print("调试信息: 页面中的所有链接")
        all_links = driver.find_elements(By.TAG_NAME, "a")
        for i, link in enumerate(all_links[:10]):
            href = link.get_attribute("href")
            text = link.text.strip()
            print(f"  链接 {i+1}: {href} - 文本: {text[:30]}...")

    return unique_links


def main():
    print("📌 欢迎使用中国政府采购网爬虫")

    province_map = {
        "重庆": "chongqing",
        "江苏": "jiangsu",
        "广东": "guangdong",
        "山东": "shandong",
        "湖北": "hubei",
        "浙江": "zhejiang"

    province_name = input(f"请输入省份 (支持: {', '.join(province_map.keys())}): ").strip()
    if province_name not in province_map:
        print(f"错误：不支持的省份 '{province_name}'。")
        return
        
    province_pinyin = province_map[province_name]

    start_date = input("请输入开始日期（YYYY-MM-DD）：").strip()
    end_date = input("请输入结束日期（YYYY-MM-DD）：").strip()
    keyword = "空调"

    try:
        parser_module = importlib.import_module(f"detail_parsers.{province_pinyin}")
        get_parser_for_url = getattr(parser_module, 'get_parser_for_url')
        get_dynamic_html = getattr(parser_module, 'get_dynamic_html')
        print(f"✅ 成功加载模块: detail_parsers.{province_pinyin}")
    except (ImportError, AttributeError) as e:
        print(f"❌ 无法加载省份 '{province_name}' 的解析模块: {e}")
        return

    print("\n🔍 正在抓取 " + province_name + " 地区，关键词" + keyword + " 中标公告")
    print(f"📅 时间范围：{start_date} ~ {end_date}")

    chrome_options = Options()
    # 开启可视化浏览器调试
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')

    driver = webdriver.Chrome(options=chrome_options)

    all_data = []
    page = 1

    while True:
        url = build_ccgp_search_url(province_name, start_date, end_date, keyword, page)
        print(f"\n📄 第 {page} 页：{url}")
        driver.get(url)

        links = get_project_links_from_page(driver)
        if not links:
            print("📭 当前页无有效项目链接，结束抓取")
            break

        for i, link in enumerate(links, 1):
            print(f"🔗 [{i}/{len(links)}] 正在抓取详情页: {link}")
            try:
                parser = get_parser_for_url(link)
                if not parser:
                    print(f"    [警告] 无法为链接找到合适的解析器，已跳过。")
                    continue
                
                parser_type = 'local' if "dfgg" in link else 'central'
                detail_html = get_dynamic_html(link, parser_type=parser_type)
                
                if not detail_html:
                    print(f"    [警告] 无法获取链接的HTML内容，已跳过。")
                    continue
                    
                parsed_data_list = parser.parse(detail_html)
                if parsed_data_list:
                    print(f"    ✅ 解析成功，获得 {len(parsed_data_list)} 条记录。")
                    # Add common info to each record
                    for data_dict in parsed_data_list:
                        data_dict.update({
                            "链接": link,
                            "省份": province_name
                        })
                    all_data.extend(parsed_data_list)
                else:
                    print(f"    [警告] 解析器未能从此链接提取到数据。")

            except Exception as e:
                print(f"    ❌ 处理链接 {link} 时发生未知错误: {e}")

        # 尝试点击"下一页"
        try:
            next_button = driver.find_element(By.LINK_TEXT, "下一页")
            driver.execute_script("arguments[0].click();", next_button)
            page += 1
            time.sleep(2)
        except:
            print("✅ 没有更多页面")
            break

    driver.quit()

    if all_data:
        df = pd.DataFrame(all_data)
        filename = f"output/中标公告_{keyword}_{province_name}_{start_date}_to_{end_date}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n✅ 成功抓取 {len(all_data)} 条数据，已保存至：{filename}")
    else:
        print("❌ 没有成功提取任何数据")


if __name__ == "__main__":
    main()
