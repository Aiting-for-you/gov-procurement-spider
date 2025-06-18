# cleaner.py

import pandas as pd
import os
import re

def clean_report_by_keywords(file_path: str, keywords: list, logger=None):
    """
    Cleans a CSV report file by removing rows where the '项目名称' column
    contains any of the specified keywords. The original file is overwritten.

    Args:
        file_path (str): The absolute path to the _report.csv file.
        keywords (list): A list of strings to search for in the '项目名称' column.
        logger: A logger object (optional) for logging messages.

    Returns:
        tuple: A tuple containing a status string ('SUCCESS', 'ERROR', 'INFO') 
               and a summary message.
    """
    def log_message(msg):
        if logger and hasattr(logger, 'put'):
            logger.put(msg)
        elif logger:
             logger.info(msg)
        else:
            print(msg)

    if not os.path.exists(file_path):
        return ('ERROR', f"文件不存在: {file_path}")

    if not keywords:
        return ('INFO', "未提供任何关键词，无需清洗。")

    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        
        # Ensure the '项目名称' column exists
        if '项目名称' not in df.columns:
            return ('ERROR', f"文件中缺少 '项目名称' 列。")

        initial_row_count = len(df)

        # Create a regex pattern: '维保|服务'
        # The pattern is case-insensitive (case=False)
        pattern = '|'.join(map(re.escape, keywords))
        
        # Filter rows to KEEP: rows where '项目名称' does NOT contain the keywords.
        # na=False ensures that NaN values in the column are treated as not containing the keywords.
        df_cleaned = df[~df['项目名称'].str.contains(pattern, case=False, na=False, regex=True)]

        rows_removed = initial_row_count - len(df_cleaned)

        if rows_removed == 0:
            summary = f"文件 '{os.path.basename(file_path)}' 中未找到包含指定关键词的行。\n\n无需改动。"
            return ('INFO', summary)
        
        # Overwrite the original file with the cleaned data
        df_cleaned.to_csv(file_path, index=False, encoding='utf-8-sig')

        summary = (
            f"数据清洗完成！\n\n"
            f"文件: {os.path.basename(file_path)}\n"
            f"原始行数: {initial_row_count}\n"
            f"移除行数: {rows_removed}\n"
            f"剩余行数: {len(df_cleaned)}\n\n"
            f"文件已覆盖保存。"
        )
        return ('SUCCESS', summary)

    except Exception as e:
        log_message(f"清洗文件时发生错误: {e}")
        import traceback
        log_message(traceback.format_exc())
        return ('ERROR', f"处理文件时发生未知错误: {e}") 