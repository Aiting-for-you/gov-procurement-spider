import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from urllib3.exceptions import MaxRetryError
import importlib
import os
import traceback

from url_builder import build_ccgp_search_url

def start_crawl_process(province_pinyin, province_cn, keyword, start_date, end_date, logger, output_dir='output'):
    """
    Main process to start the web crawler for a given province.
    This function now accepts a logger and an output directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    safe_province_name = province_cn.replace(" ", "_")
    filename = os.path.join(output_dir, f"{safe_province_name}_{keyword}_{start_date}_to_{end_date}.csv")
    
    logger.put(f"准备开始抓取: {province_cn} - {keyword}")
    logger.put(f"日期范围: {start_date} to {end_date}")
    logger.put(f"结果将保存至: {filename}")

    try:
        try:
            parser_module = importlib.import_module(f"detail_parsers.{province_pinyin}")
            ParserClass = getattr(parser_module, 'Parser')
        except (ImportError, AttributeError) as e:
            logger.put(f"错误：无法为省份 '{province_cn}' 加载解析器模块。请检查 'detail_parsers/{province_pinyin}.py' 是否存在且包含 'Parser' 类。")
            logger.put(f"详细错误: {e}")
            logger.put("CRAWL_FAILED")
            return
            
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)

        with driver:
            parser_instance = ParserClass(driver, build_ccgp_search_url, logger.put, province_cn, keyword, start_date, end_date)
            results = parser_instance.get_and_parse_results()
            
            if results:
                df = pd.DataFrame(results)
                df.to_csv(filename, index=False, encoding='utf-8-sig')
                logger.put(f"成功抓取 {len(results)} 条数据，已保存到 {filename}")
            else:
                logger.put("未找到相关数据或解析失败。")

    except (WebDriverException, MaxRetryError) as e:
        logger.put(f"驱动或网络连接失败: {e}")
        logger.put("请确保Chrome浏览器已安装且版本兼容。")
        logger.put("CRAWL_FAILED")
        return
    except Exception as e:
        logger.put(f"初始化或抓取过程中发生未知错误: {e}")
        logger.put(traceback.format_exc())
        logger.put("CRAWL_FAILED")
        return

    logger.put("CRAWL_COMPLETE")

if __name__ == '__main__':
    
    PROVINCE_PINYIN_MAP = {
        "安徽": "anhui", "重庆": "chongqing", "广东": "guangdong", "广西": "guangxi", 
        "河北": "hebei", "湖北": "hubei", "江苏": "jiangsu", "山东": "shandong", 
        "四川": "sichuan", "浙江": "zhejiang"
    }

    print("可用的省份列表:")
    for key in PROVINCE_PINYIN_MAP:
        print(f"- {key}")
    
    province_chinese = input("请输入省份中文名: ")
    province_pinyin = PROVINCE_PINYIN_MAP.get(province_chinese)

    if not province_pinyin:
        print("输入的省份无效。")
        exit()

    keyword = input("请输入关键词: ")
    start_date = input("请输入开始日期 (YYYY-MM-DD): ")
    end_date = input("请输入结束日期 (YYYY-MM-DD): ")

    class DummyQueue:
        def put(self, message):
            if message not in ["CRAWL_COMPLETE", "CRAWL_FAILED"]:
                print(message)

    start_crawl_process(
        province_pinyin,
        province_chinese,
        keyword,
        start_date,
        end_date,
        DummyQueue()
    )
