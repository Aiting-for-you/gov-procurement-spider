# url_builder.py

from urllib.parse import quote

# 支持的省份与行政编码映射
PROVINCE_ZONE_MAP = {
    "北京": "11", "天津": "12", "河北": "13", "山西": "14", "内蒙古": "15",
    "辽宁": "21", "吉林": "22", "黑龙江": "23", "上海": "31", "江苏": "32",
    "浙江": "33", "安徽": "34", "福建": "35", "江西": "36", "山东": "37",
    "河南": "41", "湖北": "42", "湖南": "43", "广东": "44", "广西": "45",
    "海南": "46", "重庆": "50", "四川": "51", "贵州": "52", "云南": "53",
    "西藏": "54", "陕西": "61", "甘肃": "62", "青海": "63", "宁夏": "64",
    "新疆": "65"
}

def build_ccgp_search_url(province: str, start_date: str, end_date: str, keyword="空调", page=1) -> str:
    """构造政府采购网搜索URL（货物类，中标公告）"""
    zone_id = PROVINCE_ZONE_MAP.get(province)
    if not zone_id:
        raise ValueError(f"省份未支持：{province}")

    return (
        "https://search.ccgp.gov.cn/bxsearch?"
        f"searchtype=1&page_index={page}&bidSort=0&buyerName=&projectId="
        f"&pinMu=1&bidType=7&dbselect=bidx"
        f"&kw={quote(keyword)}"
        f"&start_time={start_date.replace('-', ':')}"
        f"&end_time={end_date.replace('-', ':')}"
        f"&timeType=6&displayZone={quote(province)}&zoneId={zone_id}"
        f"&pppStatus=0&agentName="
    )
