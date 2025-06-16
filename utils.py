# 工具方法（如日期处理、日志）
# utils.py

from datetime import datetime

def in_date_range(date_str, start, end):
    """检查日期是否在指定范围内"""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return start <= d <= end
    except:
        return False
