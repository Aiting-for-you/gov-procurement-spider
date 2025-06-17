import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

import asyncio
import importlib
import pprint
import traceback
from playwright.async_api import async_playwright

# 待测试的省份 -> URL 映射
# (稍后会补全所有省份)
TEST_CASES = [
    {"province": "hubei", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202407/t20240726_22731140.htm"},
    {"province": "shandong", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202411/t20241126_23718366.htm"},
    {"province": "chongqing", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202506/t20250610_24749794.htm"},
    {"province": "sichuan", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202411/t20241112_23596096.htm"},
    {"province": "zhejiang", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202410/t20241016_23383346.htm"},
    {"province": "guangxi", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202411/t20241113_23612615.htm"},
    {"province": "jiangsu", "url": "http://www.ccgp-jiangsu.gov.cn/jiangsu/cggg/zbgg/202405/t20240523_1215325.html"},
    # 广东的3个URL
    {"province": "guangdong", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202505/t20250527_24670758.htm"},
    {"province": "guangdong", "url": "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202502/t20250221_24197324.htm"},
    {"province": "guangdong", "url": "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202505/t20250522_24642661.htm"},
    # 保留未提供链接的省份
    {"province": "hunan", "url": ""},
    {"province": "hebei", "url": ""},
    {"province": "anhui", "url": ""},
]

async def fetch_page_content(url):
    """
    使用 Playwright 异步获取指定 URL 的页面内容。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            await asyncio.sleep(5) # 等待动态内容加载
            content = await page.content()
            return content
        except Exception as e:
            print(f"页面加载错误: {e}")
            return None
        finally:
            await browser.close()

def validate_data(data):
    """
    验证解析出的数据是否符合基本要求
    """
    if not data:
        return False, "解析结果为空"
    
    required_fields = ['project_name', 'project_number', 'winning_supplier', 'winning_amount']
    missing_fields = [field for field in required_fields if data.get(field) in [None, 'N/A', '']]
    
    if missing_fields:
        return False, f"缺少关键字段: {', '.join(missing_fields)}"
        
    return True, "所有关键字段都已成功解析"


async def run_batch_tests():
    """
    自动化批量测试函数：循环测试所有省份，并打印解析结果。
    """
    for case in TEST_CASES:
        province, url = case["province"], case["url"]
        if not url:
            print(f"--- [ 跳过 {province.upper()} ] - 未提供URL ---\n")
            continue

        print(f"--- [ 正在测试 {province.upper()} ] URL: {url} ---")
        
        try:
            # 1. 动态导入模块和函数
            parser_module_name = f"detail_parsers.{province}"
            parser_module = importlib.import_module(parser_module_name)
            
            parser = parser_module.get_parser_for_url(url)
            if not parser:
                print(f"❌ 错误: 在 {parser_module_name} 中没有为该URL找到合适的解析器。\n")
                continue

            # 获取HTML
            html = await fetch_page_content(url)
            if not html:
                print("❌ 错误: 无法获取HTML内容。\n")
                continue
            
            # 2. 调用解析器
            results = parser.parse(html)
            
            # 3. 验证并打印结果
            if not results:
                print(f"❌ 解析失败: 解析器未返回任何数据。")
                is_valid, message, data_to_show = False, "解析器未返回任何数据", {}
            else:
                # 兼容返回列表和单个字典的情况
                data = results[0] if isinstance(results, list) else results
                is_valid, message = validate_data(data)
                data_to_show = data

            if is_valid:
                print(f"✅ 解析成功! {message}")
                pprint.pprint(data_to_show)
            else:
                print(f"❌ 解析失败: {message}")
                pprint.pprint(data_to_show) # 打印部分成功的数据以供调试
            
            print("-" * 50 + "\n")

        except ImportError:
            print(f"❌ 错误: 无法导入解析器模块: {parser_module_name}\n")
        except Exception as e:
            print(f"❌ 测试过程中出现未知错误: {e}")
            traceback.print_exc()
            print("-" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(run_batch_tests()) 