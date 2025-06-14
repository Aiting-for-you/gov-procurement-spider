# main.py

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import importlib
import os

from url_builder import build_ccgp_search_url


def get_project_links_from_page(driver, logger):
    """从当前页面获取项目链接"""
    project_links = []

    try:
        wait = WebDriverWait(driver, 10)

        logger(f"页面标题: {driver.title}")
        logger(f"当前URL: {driver.current_url}")

        try:
            result_container = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".vT-srch-result-list-bid"))
            )
            logger("找到搜索结果容器")
            link_elements = result_container.find_elements(By.CSS_SELECTOR, "li a[href]")
            logger(f"在结果容器中找到 {len(link_elements)} 个链接")

            for element in link_elements:
                href = element.get_attribute("href")
                if href and ("ccgp.gov.cn" in href and (".htm" in href or "detail" in href)):
                    project_links.append(href)
        except TimeoutException:
            logger("未找到标准搜索结果容器，尝试备用选择器")
            selectors = [
                ".vT-srch-result-list-bid a", "a[href*='ccgp.gov.cn'][href*='.htm']"
            ]
            for selector in selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    logger(f"使用选择器 '{selector}' 找到 {len(elements)} 个链接")
                    for element in elements:
                        href = element.get_attribute("href")
                        if href and "ccgp.gov.cn" in href and (".htm" in href or "detail" in href):
                            project_links.append(href)
                    if project_links:
                        break

    except Exception as e:
        logger(f"获取项目链接时出错: {e}")

    unique_links = list(set(project_links))
    logger(f"总共找到 {len(unique_links)} 个唯一项目链接")
    return unique_links


def start_crawl_process(province_pinyin, province_cn, keyword, start_date, end_date, logger=print):
    """
    爬虫主流程
    :param province_pinyin: 省份拼音，用于加载模块
    :param province_cn: 省份中文名，用于搜索和文件名
    :param keyword: 搜索关键词
    :param start_date: 开始日期 YYYY-MM-DD
    :param end_date: 结束日期 YYYY-MM-DD
    :param logger: 日志记录函数，默认为 print
    """
    try:
        parser_module = importlib.import_module(f"detail_parsers.{province_pinyin}")
        get_parser_for_url = getattr(parser_module, 'get_parser_for_url')
        get_dynamic_html = getattr(parser_module, 'get_dynamic_html')
        logger(f"✅ 成功加载模块: detail_parsers.{province_pinyin}")
    except (ImportError, AttributeError) as e:
        logger(f"❌ 无法加载省份 '{province_cn}' 的解析模块: {e}")
        raise

    logger(f'\n🔍 正在抓取 {province_cn} 地区，关键词"{keyword}"')
    logger(f"📅 时间范围：{start_date} ~ {end_date}")

    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    driver = webdriver.Chrome(options=chrome_options)

    all_data = []
    page = 1

    try:
        while True:
            url = build_ccgp_search_url(province_cn, start_date, end_date, keyword, page)
            logger(f"\n📄 第 {page} 页：{url}")
            driver.get(url)

            links = get_project_links_from_page(driver, logger)
            if not links:
                logger("📭 当前页无有效项目链接，结束抓取")
                break

            for i, link in enumerate(links, 1):
                logger(f"🔗 [{i}/{len(links)}] 抓取详情: {link[:80]}...")
                try:
                    parser = get_parser_for_url(link)
                    if not parser:
                        logger(f"    [警告] 未找到解析器，已跳过。")
                        continue
                    
                    parser_type = 'local' if "dfgg" in link else 'central'
                    detail_html = get_dynamic_html(link, parser_type=parser_type)
                    
                    if not detail_html:
                        logger(f"    [警告] 未获取到HTML内容，已跳过。")
                        continue
                        
                    parsed_data_list = parser.parse(detail_html)
                    if parsed_data_list:
                        logger(f"    ✅ 解析成功，获得 {len(parsed_data_list)} 条记录。")
                        for data_dict in parsed_data_list:
                            data_dict.update({"链接": link, "省份": province_cn})
                        all_data.extend(parsed_data_list)
                    else:
                        logger(f"    [警告] 解析器未能提取到数据。")

                except Exception as e:
                    logger(f"    ❌ 处理链接时发生错误: {e}")

            try:
                next_button = driver.find_element(By.LINK_TEXT, "下一页")
                driver.execute_script("arguments[0].click();", next_button)
                page += 1
                time.sleep(2)
            except:
                logger("✅ 没有更多页面")
                break
    finally:
        driver.quit()

    if all_data:
        # Create output dir if not exists
        if not os.path.exists('output'):
            os.makedirs('output')
        
        df = pd.DataFrame(all_data)
        filename = f"output/中标公告_{keyword}_{province_cn}_{start_date}_to_{end_date}.csv"
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger(f"\n✅ 成功抓取 {len(all_data)} 条数据，已保存至：{filename}")
    else:
        logger("❌ 没有成功提取任何数据")


def main_cli():
    """命令行交互版本的主函数"""
    print("📌 欢迎使用中国政府采购网爬虫 (命令行版)")

    # 动态获取省份列表
    parsers_dir = os.path.join(os.path.dirname(__file__), 'detail_parsers')
    province_files = [f.replace('.py', '') for f in os.listdir(parsers_dir) if f.endswith('.py') and not f.startswith('__') and f != 'base.py' and f != 'test.py']
    
    # 建立一个简易的中文到拼音的映射
    # 注意：这里需要手动维护，或者从一个更可靠的数据源生成
    province_cn_map = {
        'anhui': '安徽', 'chongqing': '重庆', 'guangdong': '广东', 'guangxi': '广西', 
        'hebei': '河北', 'hubei': '湖北', 'jiangsu': '江苏', 'shandong': '山东', 
        'sichuan': '四川', 'zhejiang': '浙江' 
        # 其他省份...
    }
    supported_provinces_cn = [province_cn_map.get(p, p) for p in sorted(province_files)]
    pinyin_cn_map = {v: k for k, v in province_cn_map.items()}


    print(f"支持的省份: {', '.join(supported_provinces_cn)}")
    province_cn_input = input("请输入省份中文名 (例如: 江苏): ").strip()
    
    province_pinyin_input = pinyin_cn_map.get(province_cn_input)

    if not province_pinyin_input:
        print(f"错误：不支持的省份 '{province_cn_input}'。")
        return
        
    keyword = input("请输入关键词 (例如: 空调): ").strip()
    start_date = input("请输入开始日期 (YYYY-MM-DD): ").strip()
    end_date = input("请输入结束日期 (YYYY-MM-DD): ").strip()

    if not all([province_pinyin_input, keyword, start_date, end_date]):
        print("错误：所有输入项都不能为空。")
        return

    start_crawl_process(province_pinyin_input, province_cn_input, keyword, start_date, end_date)


if __name__ == "__main__":
    main_cli()