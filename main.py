import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from urllib3.exceptions import MaxRetryError
import importlib
import os
import traceback
import argparse
import logging

from province_mapping import get_province_pinyin
from logger_config import get_logger, QueueHandler
from report_generator import create_formatted_report
from url_builder import build_ccgp_search_url

# webdriver-manager is now a dependency
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


def start_crawl_process(province_pinyin, province_cn, keyword, start_date, end_date, output_dir='output', log_queue=None):
    """
    重构后的主流程，负责处理列表页抓取和详情页解析调度。
    """
    # 1. Setup Logger
    logger = get_logger(f"crawler.{province_pinyin}")
    if log_queue:
        logger.addHandler(QueueHandler(log_queue))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    safe_province_name = province_cn.replace(" ", "_")
    filename = os.path.join(output_dir, f"{safe_province_name}_{keyword}_{start_date}_to_{end_date}.csv")
    
    logger.info(f"准备开始抓取: {province_cn} - {keyword}")
    logger.info(f"日期范围: {start_date} to {end_date}")
    logger.info(f"结果将保存至: {filename}")

    # 2. 动态加载省份解析模块
    try:
        parser_module = importlib.import_module(f"detail_parsers.{province_pinyin}")
        get_parser_for_url = getattr(parser_module, 'get_parser_for_url')
        get_dynamic_html = getattr(parser_module, 'get_dynamic_html')
    except (ImportError, AttributeError) as e:
        logger.error(f"错误：无法为省份 '{province_cn}' 加载解析器模块或必要函数。")
        logger.error(f"请检查 'detail_parsers/{province_pinyin}.py' 是否符合规范。")
        logger.error(f"详细错误: {e}")
        if log_queue: log_queue.put("CRAWL_FAILED")
        return
            
    # 3. 初始化Selenium WebDriver
    all_results = []
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except (WebDriverException, MaxRetryError, ValueError) as e:
            logger.error(f"无法启动WebDriver: {e}")
            logger.error("请确保Chrome浏览器已正确安装且ChromeDriver版本兼容。")
            if log_queue: log_queue.put("CRAWL_FAILED")
            return

        # 4. 循环抓取所有列表页，获取详情页链接
        page = 1
        all_detail_links = []
        while True:
            search_url = build_ccgp_search_url(province_cn, start_date, end_date, keyword, page)
            logger.info(f"\n📄 正在抓取列表页 第 {page} 页...")
            driver.get(search_url)

            try:
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".vT-srch-result-list-bid li a")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '抱歉，没有找到相关数据')]"))
                    )
                )

                if "抱歉，没有找到相关数据" in driver.page_source:
                    if page == 1:
                        logger.info("📭 在起始页未找到任何数据，任务提前结束。")
                    else:
                        logger.info("✅ 已到达结果末尾，列表抓取完成。")
                    break

                link_elements = driver.find_elements(By.CSS_SELECTOR, ".vT-srch-result-list-bid li a")
                page_links = [link.get_attribute('href') for link in link_elements if link.get_attribute('href')]
                
                if not page_links:
                    logger.info("📭 当前页没有找到链接，可能已是最后一页。")
                    break
                
                all_detail_links.extend(page_links)
                logger.info(f"    找到 {len(page_links)} 个链接，累计 {len(all_detail_links)} 个。")

                next_button = driver.find_element(By.LINK_TEXT, "下一页")
                driver.execute_script("arguments[0].click();", next_button)
                page += 1
                time.sleep(2)
            except TimeoutException:
                logger.info("📭 页面加载超时或未找到结果列表，结束列表抓取。")
                break
            except NoSuchElementException:
                logger.info("✅ 没有'下一页'按钮，列表抓取完成。")
                break

        # 5. 遍历详情页链接，进行解析
        unique_links = sorted(list(set(all_detail_links)), key=lambda x: all_detail_links.index(x))
        logger.info(f"\n🔎 开始处理 {len(unique_links)} 个详情页链接...")
        
        if not unique_links:
             logger.info("🤷‍♀️ 未收集到任何详情页链接，任务结束。")
        
        for i, link in enumerate(unique_links, 1):
            logger.info(f"    🔗 [{i}/{len(unique_links)}] 正在处理...")
            parser_instance = get_parser_for_url(link)
            if not parser_instance:
                logger.warning(f"        [警告] 未能为链接找到合适的解析器，已跳过。")
                continue

            html = get_dynamic_html(link)
            if not html:
                logger.warning(f"        [警告] 未能获取页面内容，已跳过。")
                continue

            try:
                parsed_data = parser_instance.parse(html)
                if parsed_data:
                    for item in parsed_data:
                        item["链接"] = link
                        item["省份"] = province_cn
                    all_results.extend(parsed_data)
                    logger.info(f"        ✅ 解析成功，获得 {len(parsed_data)} 条记录。")
                else:
                    logger.info(f"        [提示] 解析器返回空，页面可能无有效信息。")
            except Exception as e:
                logger.error(f"        ❌ 解析时发生错误: {e}")

    except Exception as e:
        logger.error(f"抓取过程中发生未知严重错误: {e}")
        logger.error(f"详细堆栈信息: {traceback.format_exc()}")
        if log_queue: log_queue.put("CRAWL_FAILED")
        return
    finally:
        if driver:
            driver.quit()

    # 6. 保存结果
    if all_results:
        df = pd.DataFrame(all_results)
        standard_columns = [
            "发布日期", "项目号", "采购方式", "项目名称", "供应商名称",
            "中标金额", "名称", "品牌", "规格型号", "数量", "单价",
            "链接", "省份"
        ]
        final_columns = [col for col in standard_columns if col in df.columns]
        df = df[final_columns]
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        logger.info(f"\n🎉 成功抓取 {len(all_results)} 条数据，已保存到 {filename}")
        if log_queue: log_queue.put(f"CRAWL_SUCCESS:{filename}")
    else:
        logger.info("\n🤷‍♀️ 本次任务未找到任何可解析的数据。")

    if log_queue: log_queue.put("CRAWL_COMPLETE")
    return filename


def main():
    parser = argparse.ArgumentParser(description="政府采购数据爬虫")
    parser.add_argument("--province", help="省份拼音")
    parser.add_argument("--keyword", help="关键词")
    parser.add_argument("--start_date", help="开始日期 (YYYY-MM-DD)")
    parser.add_argument("--end_date", help="结束日期 (YYYY-MM-DD)")
    parser.add_argument("--output", default="output", help="输出目录")
    parser.add_argument(
        "--format_report",
        metavar="FILE_PATH",
        nargs='?',
        const=True,
        default=False,
        help="仅执行报告格式化功能。可选择性提供CSV文件路径，否则将在output文件夹中查找最新的CSV文件。"
    )
    args = parser.parse_args()

    # Setup a general logger for the main script
    cli_logger = get_logger("main_cli")

    if args.format_report:
        # For formatting, we can just use the logger directly.
        # The report generator will use this logger to print messages.
        target_file = args.format_report
        if target_file is True:
            output_dir = 'output'
            files = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.endswith('.csv') and not f.endswith('_report.csv') and not f.endswith('_processed.csv')]
            if not files:
                cli_logger.error("错误：在 'output' 目录中未找到可格式化的CSV文件。")
                exit(1)
            target_file = max(files, key=os.path.getctime)
            cli_logger.info(f"未指定文件，自动选择最新的文件进行格式化: {os.path.basename(target_file)}")

        if not os.path.exists(target_file):
            cli_logger.error(f"错误：指定的文件不存在: {target_file}")
            exit(1)
            
        create_formatted_report(target_file, cli_logger)
        exit(0)

    if not all([args.province, args.keyword, args.start_date, args.end_date]):
        parser.error("执行爬取任务时，必须提供 --province, --keyword, --start_date, 和 --end_date 参数。")

    province_cn = get_province_pinyin(args.province)
    if not province_cn:
        parser.error(f"无效的省份拼音: '{args.province}'")

    # When running from CLI, we don't have a queue. The logger will just print to console/file.
    start_crawl_process(
        args.province,
        province_cn,
        args.keyword,
        args.start_date,
        args.end_date,
        args.output,
        log_queue=None 
    )

if __name__ == "__main__":
    main()
