import asyncio
from playwright.async_api import async_playwright
import time

async def fetch_page_content(url):
    """
    使用 Playwright 异步获取指定 URL 的页面内容。
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            await page.goto(url, wait_until='networkidle', timeout=60000)
            # 等待一些时间确保动态内容加载
            await asyncio.sleep(5)
            content = await page.content()
            print(content)
        except Exception as e:
            print(f"An error occurred: {e}")
            return None
        finally:
            await browser.close()
    return content

async def main():
    """
    主函数，用于执行页面内容获取。
    """
    # 用户提供的第一个URL
    url = "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202505/t20250527_24670758.htm"
    print(f"Fetching content for {url}...")
    html_content = await fetch_page_content(url)
    if html_content:
        # 可以选择将内容保存到文件以便分析
        with open("guangdong_page.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("Content saved to guangdong_page.html")

if __name__ == "__main__":
    asyncio.run(main()) 