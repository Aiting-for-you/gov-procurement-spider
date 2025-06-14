# 参数配置（搜索模板、地区编码等）
# config.py

# 地区编码映射（根据 search.ccgp.gov.cn 参数 zoneId）
PROVINCE_CODE_MAP = {
    "江苏": "32",
    "浙江": "33",
    "山东": "37",
    "广东": "44",
    "湖北": "42",
    "重庆": "50"
}

# 搜索结果URL模板（自动填充）
SEARCH_URL_TEMPLATE = (
    "https://search.ccgp.gov.cn/bxsearch?"
    "searchtype=1&page_index={page}&bidSort=0&buyerName=&projectId=&pinMu=1&bidType=7"
    "&dbselect=bidx&kw={keyword}&start_time={start}&end_time={end}&timeType=6"
    "&displayZone={province_name}&zoneId={zone_id}&pppStatus=0&agentName="
)
