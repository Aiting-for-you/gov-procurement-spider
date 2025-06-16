import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import importlib
import os
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import MaxRetryError
import traceback

from url_builder import build_ccgp_search_url


def get_project_links_from_page(driver, logger):
    project_links = []
    try:
        wait = WebDriverWait(driver, 5) 
        result_container = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".vT-srch-result-list-bid"))
        )
        link_elements = result_container.find_elements(By.CSS_SELECTOR, "li a[href]")

        for element in link_elements:
            href = element.get_attribute("href")
            if href and ("ccgp.gov.cn" in href and (".htm" in href or "detail" in href)):
                project_links.append(href)
    except TimeoutException:
        logger(f"在5秒内未找到指定的链接容器，此页面可能无结果。")
    except Exception as e:
        logger(f"在当前页获取项目链接时出错: {e}")
    return project_links


def start_crawl_process(province_pinyin, province_cn, keyword, start_date, end_date, logger, output_dir='output'):
    """
    重构后的主流程，负责处理列表页抓取和详情页解析调度。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    safe_province_name = province_cn.replace(" ", "_")
    filename = os.path.join(output_dir, f"{safe_province_name}_{keyword}_{start_date}_to_{end_date}.csv")
    
    # 统一使用 put 方法记录日志
    log_func = logger.put if hasattr(logger, 'put') else print

    log_func(f"准备开始抓取: {province_cn} - {keyword}")
    log_func(f"日期范围: {start_date} to {end_date}")
    log_func(f"结果将保存至: {filename}")

    # 1. 动态加载省份解析模块
    try:
        parser_module = importlib.import_module(f"detail_parsers.{province_pinyin}")
        get_parser_for_url = getattr(parser_module, 'get_parser_for_url')
        get_dynamic_html = getattr(parser_module, 'get_dynamic_html')
    except (ImportError, AttributeError) as e:
        log_func(f"错误：无法为省份 '{province_cn}' 加载解析器模块或必要函数。")
        log_func(f"请检查 'detail_parsers/{province_pinyin}.py' 是否符合规范。")
        log_func(f"详细错误: {e}")
        if hasattr(logger, 'put'): logger.put("CRAWL_FAILED")
        return
            
    # 2. 初始化Selenium WebDriver
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
            log_func(f"无法启动WebDriver: {e}")
            log_func("请确保Chrome浏览器已正确安装且ChromeDriver版本兼容。")
            if hasattr(logger, 'put'): logger.put("CRAWL_FAILED")
            return

        # 3. 循环抓取所有列表页，获取详情页链接
        page = 1
        all_detail_links = []
        while True:
            search_url = build_ccgp_search_url(province_cn, start_date, end_date, keyword, page)
            log_func(f"\n📄 正在抓取列表页 第 {page} 页...")
            # log_func(search_url) # Uncomment for debugging
            driver.get(search_url)

            try:
                # 等待页面核心内容加载
                WebDriverWait(driver, 10).until(
                    EC.any_of(
                        EC.presence_of_element_located((By.CSS_SELECTOR, ".vT-srch-result-list-bid li a")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '抱歉，没有找到相关数据')]"))
                    )
                )

                # 检查是否没有结果
                if "抱歉，没有找到相关数据" in driver.page_source:
                    if page == 1:
                        log_func("📭 在起始页未找到任何数据，任务提前结束。")
                    else:
                        log_func("✅ 已到达结果末尾，列表抓取完成。")
                    break

                link_elements = driver.find_elements(By.CSS_SELECTOR, ".vT-srch-result-list-bid li a")
                page_links = [link.get_attribute('href') for link in link_elements if link.get_attribute('href')]
                
                if not page_links:
                    log_func("📭 当前页没有找到链接，可能已是最后一页。")
                    break
                
                all_detail_links.extend(page_links)
                log_func(f"    找到 {len(page_links)} 个链接，累计 {len(all_detail_links)} 个。")

                # 尝试点击下一页
                next_button = driver.find_element(By.LINK_TEXT, "下一页")
                driver.execute_script("arguments[0].click();", next_button)
                page += 1
                time.sleep(2) # 等待页面跳转
            except TimeoutException:
                log_func("📭 页面加载超时或未找到结果列表，结束列表抓取。")
                break
            except NoSuchElementException:
                log_func("✅ 没有'下一页'按钮，列表抓取完成。")
                break

        # 4. 遍历详情页链接，进行解析
        unique_links = sorted(list(set(all_detail_links)), key=lambda x: all_detail_links.index(x))
        log_func(f"\n🔎 开始处理 {len(unique_links)} 个详情页链接...")
        
        if not unique_links:
             log_func("🤷‍♀️ 未收集到任何详情页链接，任务结束。")
        
        for i, link in enumerate(unique_links, 1):
            log_func(f"    🔗 [{i}/{len(unique_links)}] 正在处理...")
            # log_func(f"    {link}") # Uncomment for debugging

            # a. 根据URL获取合适的解析器实例
            parser_instance = get_parser_for_url(link)
            if not parser_instance:
                log_func(f"        [警告] 未能为链接找到合适的解析器，已跳过。")
                continue

            # b. 获取动态HTML
            html = get_dynamic_html(link)
            if not html:
                log_func(f"        [警告] 未能获取页面内容，已跳过。")
                continue

            # c. 解析页面
            try:
                parsed_data = parser_instance.parse(html)
                if parsed_data:
                    # d. 由主程序统一添加 `链接` 和 `省份` 字段
                    for item in parsed_data:
                        item["链接"] = link
                        item["省份"] = province_cn
                    all_results.extend(parsed_data)
                    log_func(f"        ✅ 解析成功，获得 {len(parsed_data)} 条记录。")
                else:
                    log_func(f"        [提示] 解析器返回空，页面可能无有效信息。")
            except Exception as e:
                log_func(f"        ❌ 解析时发生错误: {e}")
                # log_func(f"        详细信息: {traceback.format_exc()}") # Uncomment for debugging

    except Exception as e:
        log_func(f"抓取过程中发生未知严重错误: {e}")
        log_func(f"详细堆栈信息: {traceback.format_exc()}")
        if hasattr(logger, 'put'): logger.put("CRAWL_FAILED")
        return
    finally:
        if driver:
            driver.quit()

    # 5. 保存结果
    if all_results:
        df = pd.DataFrame(all_results)
        # 按照规范中定义的最终顺序排列字段
        standard_columns = [
            "发布日期", "项目号", "采购方式", "项目名称", "供应商名称",
            "中标金额", "名称", "品牌", "规格型号", "数量", "单价",
            "链接", "省份"
        ]
        # 过滤掉数据中可能不存在的列，并保证顺序
        final_columns = [col for col in standard_columns if col in df.columns]
        df = df[final_columns]

        df.to_csv(filename, index=False, encoding='utf-8-sig')
        log_func(f"\n🎉 成功抓取 {len(all_results)} 条数据，已保存到 {filename}")
    else:
        log_func("\n🤷‍♀️ 本次任务未找到任何可解析的数据。")

    if hasattr(logger, 'put'): logger.put("CRAWL_COMPLETE")


# --- Main execution block for direct script run (testing) ---
if __name__ == '__main__':
    
    class DummyQueue:
        def put(self, message):
            print(message)

    # --- 测试参数 ---
    # 请根据需要修改以下参数进行测试
    test_province_pinyin = "chongqing"  # 例如: "sichuan"
    test_province_cn = "重庆"      # 例如: "四川"
    test_keyword = "中标"             # 例如: "中标"
    test_start_date = "2024-05-01" # 格式: YYYY-MM-DD
    test_end_date = "2024-05-10"   # 格式: YYYY-MM-DD
    test_output_dir = "output_test"
    # ----------------

    print("--- 开始直接运行测试 ---")
    start_crawl_process(
        province_pinyin=test_province_pinyin,
        province_cn=test_province_cn,
        keyword=test_keyword,
        start_date=test_start_date,
        end_date=test_end_date,
        logger=DummyQueue(),
        output_dir=test_output_dir
    )
    print("--- 测试运行结束 ---")
