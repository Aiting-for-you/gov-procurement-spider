# detail_parsers/test.py
import time
import pandas as pd
from bs4 import BeautifulSoup, NavigableString
import re
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ==============================================================================
# Local Government Announcement Parser (地方公告)
# Handles pages with /dfgg/ in URL
# ==============================================================================
class LocalGovParser:
    def find_and_extract(self, soup, label_regex, next_tag='span'):
        """通用函数，用于查找标签并提取其后的文本"""
        try:
            p_element = soup.find(lambda tag: tag.name == 'p' and re.search(label_regex, tag.get_text(strip=True)))
            if p_element and p_element.find(next_tag):
                 return p_element.find(next_tag).get_text(strip=True)
            
            # Fallback for h4 tags
            h4_element = soup.find(lambda tag: tag.name == 'h4' and re.search(label_regex, tag.get_text(strip=True)))
            if h4_element and h4_element.find_next(next_tag):
                 return h4_element.find_next(next_tag).get_text(strip=True)

        except Exception: return "N/A"
        return "N/A"

    def parse_main_bid_table(self, soup):
        """解析主要标的信息表格（地方公告版，不再拆分行）"""
        main_bid_info_list = []
        try:
            main_bid_info_title = soup.find('h4', string=re.compile(r'四、主要标的信息'))
            if not main_bid_info_title: return []

            table_container = main_bid_info_title.find_next('div', class_='panel')
            if not table_container: return []
            
            table = table_container.find('table', class_='table')
            if not table: return []

            rows = table.find_all('tr')
            if len(rows) < 2: return []

            for row in rows[1:]:
                cols = row.find_all('td')
                if not cols or len(cols) < 5: continue
                
                # 直接获取单元格的完整文本，不再拆分
                main_bid_info_list.append({
                    "名称": cols[0].get_text(strip=True),
                    "品牌": cols[1].get_text(strip=True),
                    "规格型号": cols[2].get_text(strip=True),
                    "数量": cols[3].get_text(strip=True),
                    "单价": cols[4].get_text(strip=True),
                })
        except Exception as e:
            print(f"解析地方公告表格时出错: {e}")
        return main_bid_info_list

    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        release_date = soup.find('h3', id='datecandel').get_text(strip=True).replace('发布日期：', '').strip() if soup.find('h3', id='datecandel') else 'N/A'
        project_number = self.find_and_extract(soup, r'一、项目号')
        project_name = self.find_and_extract(soup, r'二、项目名称')
        
        # 最终修正：遍历所有h4标签来查找采购方式，确保能够找到
        procurement_method = "N/A"
        try:
            h4_tags = soup.find_all('h4')
            for tag in h4_tags:
                if '采购方式' in tag.get_text():
                    match = re.search(r'采购方式：(\S+)', tag.get_text())
                    if match:
                        procurement_method = match.group(1).strip()
                        break # 找到后即跳出循环
        except Exception:
             procurement_method = "N/A"

        supplier_name = self.find_and_extract(soup, r'供应商名称')
        bid_amount = self.find_and_extract(soup, r'中标（成交）金额')
        
        main_bid_info = self.parse_main_bid_table(soup)

        final_data = []
        base_info = {
            "发布日期": release_date, "项目号": project_number, "采购方式": procurement_method,
            "项目名称": project_name, "供应商名称": supplier_name, "中标金额": bid_amount,
        }

        if not main_bid_info:
            final_data.append({**base_info, "名称": "N/A", "品牌": "N/A", "规格型号": "N/A", "数量": "N/A", "单价": "N/A"})
        else:
            for item in main_bid_info:
                final_data.append({**base_info, **item})

        return final_data

# ==============================================================================
# Central Government Announcement Parser (中央公告)
# Handles pages with /zygg/ in URL
# ==============================================================================
class CentralGovParser:
    """
    专门用于解析中央公告类型页面的解析器。
    该页面结构与地方公告差异较大。
    """
    def parse_complex_table(self, soup):
        data_rows = []
        try:
            table_title = soup.find('strong', string=re.compile(r'四、主要标的信息'))
            if not table_title: return []
            
            table = table_title.find_next('table')
            if not table: return []

            rows = table.find_all('tr')
            if len(rows) < 2: return []

            for row in rows[1:]:
                cols = row.find_all('td')
                if len(cols) < 7: continue

                # 直接获取单元格的完整文本，不再拆分
                data_rows.append({
                    "供应商名称": cols[1].get_text(strip=True),
                    "名称": cols[2].get_text(strip=True),
                    "品牌": cols[3].get_text(strip=True),
                    "规格型号": cols[4].get_text(strip=True),
                    "数量": cols[5].get_text(strip=True),
                    "单价": cols[6].get_text(strip=True),
                })

        except Exception as e:
            print(f"解析中央公告表格时出错: {e}")

        return data_rows

    def parse(self, html):
        soup = BeautifulSoup(html, 'lxml')
        
        # 最终修正：使用更健壮的lambda和正则来提取，并兼容"项目号"和"项目编号"
        project_number = "N/A"
        project_name = "N/A"
        try:
            # 兼容"项目号"和"项目编号"
            num_tag = soup.find(lambda tag: tag.name == 'strong' and '项目' in tag.get_text() and ('号' in tag.get_text() or '编号' in tag.get_text()))
            if num_tag:
                match = re.search(r'(?:项目(?:号|编号))[:：\s]*(\S+)', num_tag.get_text())
                if match:
                    project_number = match.group(1).strip()
                    if '（' in project_number:
                        project_number = project_number.split('（')[0]

            name_tag = soup.find(lambda tag: tag.name == 'strong' and '项目名称' in tag.get_text())
            if name_tag:
                match = re.search(r'项目名称[:：\s]*(.*)', name_tag.get_text())
                if match:
                    project_name = match.group(1).strip()
        except Exception:
            pass # 出错则保持"N/A"

        supplier_info_title = soup.find('strong', string=re.compile(r'三、中标（成交）信息'))
        supplier_name, bid_amount = "N/A", "N/A"
        if supplier_info_title:
            # 提取紧跟在标题后的文本节点
            supplier_name_node = supplier_info_title.find_next(string=re.compile(r'供应商名称：'))
            if supplier_name_node:
                supplier_name = supplier_name_node.replace('供应商名称：', '').strip()

            bid_amount_node = supplier_info_title.find_next(string=re.compile(r'中标（成交）金额：'))
            if bid_amount_node:
                bid_amount = bid_amount_node.replace('中标（成交）金额：', '').strip()
                # 进一步清理金额字段
                bid_amount_match = re.search(r'([\d\.]+)', bid_amount)
                if bid_amount_match:
                    bid_amount = bid_amount_match.group(1)
        
        # 再次尝试提取项目名称，以防万一
        if project_name == "N/A":
             announcement_title = soup.find('h2', class_='tc')
             if announcement_title:
                 project_name = announcement_title.get_text(strip=True).replace('中标公告','')

        # 发布日期在 class=tc 的 p 标签下的 span 中
        release_date = "N/A"
        pub_time_span = soup.find('span', id='pubTime')
        if pub_time_span:
            release_date = pub_time_span.get_text(strip=True)
        else: #备用方案
            date_p = soup.find('p', class_='tc')
            if date_p:
                release_date = date_p.find('span').get_text(strip=True)

        main_bid_info = self.parse_complex_table(soup)
        
        # 将基础信息添加到每一行表格数据中
        final_data = []
        if not main_bid_info:
             final_data.append({
                "发布日期": release_date, "项目号": project_number, "采购方式": "N/A", #中央公告无此字段
                "项目名称": project_name, "供应商名称": supplier_name, "中标金额": bid_amount,
                "名称": "N/A", "品牌": "N/A", "规格型号": "N/A", "数量": "N/A", "单价": "N/A"
            })
        else:
            for item in main_bid_info:
                item.update({
                    "发布日期": release_date, "项目号": project_number, "采购方式": "N/A",
                    "项目名称": project_name, "中标金额": bid_amount
                })
                # 如果某行没有供应商，使用顶层的供应商
                if not item.get("供应商名称"):
                    item["供应商名称"] = supplier_name
                
                # 为每一行都添加顶层项目名称
                item["项目名称"] = project_name

                final_data.append(item)
                
        return final_data

# ==============================================================================
# Parser Factory and Main Execution Logic
# ==============================================================================
def get_parser_for_url(url):
    """根据URL特征返回合适的解析器实例"""
    if "/cggg/dfgg/" in url:
        print("检测到地方公告，使用 LocalGovParser。")
        return LocalGovParser()
    elif "/cggg/zygg/" in url:
        print("检测到中央公告，使用 CentralGovParser。")
        return CentralGovParser()
    else:
        print(f"警告: 无法为URL确定解析器类型: {url}")
        return None

def get_dynamic_html(url, parser_type='local'):
    """使用Selenium获取动态加载后的HTML"""
    print("使用 Selenium 动态加载页面...")
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    
    html = ""
    try:
        driver.get(url)
        wait_element_selector = ".vF_detail_content .table tr:nth-child(2)" if parser_type == 'local' else ".vF_detail_content"
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, wait_element_selector))
        )
        print("页面动态内容加载完成。")
        html = driver.page_source
    except TimeoutException:
        print("等待动态内容超时，将使用已加载的HTML。")
        html = driver.page_source
    except Exception as e:
        print(f"Selenium加载页面时出错: {e}")
        html = driver.page_source
    finally:
        driver.quit()
    return html

def main():
    """独立测试函数，测试多个URL"""
    urls_to_test = [
        "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202504/t20250407_24403223.htm", # 地方-复杂
        "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202501/t20250110_24049384.htm", # 地方-简单
        "https://www.ccgp.gov.cn/cggg/zygg/zbgg/202506/t20250610_24748685.htm", # 中央-复杂
        "https://www.ccgp.gov.cn/cggg/dfgg/zbgg/202506/t20250610_24749794.htm"  # 地方-原始
    ]

    for url in urls_to_test:
        print(f"\n{'='*20} TESTING URL: {url} {'='*20}")
        parser = get_parser_for_url(url)
        if not parser:
            continue
        
        parser_type = 'local' if isinstance(parser, LocalGovParser) else 'central'
        html = get_dynamic_html(url, parser_type=parser_type)
        if not html:
            print("未能获取HTML内容，跳过此URL。")
            continue

        final_data_for_csv = parser.parse(html)
        
        if final_data_for_csv:
            df = pd.DataFrame(final_data_for_csv)
            column_order = ["发布日期", "项目号", "采购方式", "项目名称", "供应商名称", "中标金额", "名称", "品牌", "规格型号", "数量", "单价"]
            # 确保所有列都存在
            for col in column_order:
                if col not in df.columns:
                    df[col] = "N/A"
            df = df[column_order]

            url_id = url.split('/')[-1].replace('.htm', '')
            output_filename = f"{url_id}.csv"
            
            df.to_csv(output_filename, index=False, encoding='utf-8-sig')
            print(f"\n✅ 数据已成功保存到: {output_filename}")
            print("--- 解析结果预览 ---")
            print(df.head().to_string())
        else:
            print("\n❌ 未提取到任何数据，无法生成CSV文件。")

if __name__ == '__main__':
    main() 