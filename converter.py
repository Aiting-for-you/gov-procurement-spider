import pandas as pd
import os
import traceback

def run_converter(list_of_paths: list):
    """
    Converts a list of CSV files to XLSX format, auto-detecting encoding (UTF-8 or GBK).

    Args:
        list_of_paths (list): A list of absolute paths to the CSV files.
    
    Returns:
        tuple: A tuple containing a status code and a summary message.
    """
    if not list_of_paths:
        return ('ERROR', "没有提供任何文件用于转换。")

    success_count, skipped_count, failed_count = 0, 0, 0
    
    for csv_path in list_of_paths:
        if not csv_path or not os.path.exists(csv_path):
            failed_count += 1
            print(f"转换失败: 文件不存在或路径无效 -> {csv_path}")
            continue

        filename = os.path.basename(csv_path)
        xlsx_path = os.path.splitext(csv_path)[0] + '.xlsx'

        if os.path.exists(xlsx_path):
            skipped_count += 1
            print(f"已跳过 (Excel文件已存在): {filename}")
            continue

        try:
            if os.path.getsize(csv_path) == 0:
                failed_count += 1
                print(f"转换失败 (文件为空): {filename}")
                continue
            
            # --- New Encoding Logic ---
            try:
                df = pd.read_csv(csv_path, encoding='utf-8-sig')
            except UnicodeDecodeError:
                print(f"UTF-8 decoding failed for '{filename}', trying GBK...")
                df = pd.read_csv(csv_path, encoding='gbk')
            
            if df.empty:
                failed_count += 1
                print(f"转换失败 (文件只含表头): {filename}")
                continue

            # This part remains the same: convert and DO NOT delete
            df.to_excel(xlsx_path, index=False, engine='openpyxl')
            success_count += 1
            print(f"转换成功: {filename}")

        except Exception as e:
            failed_count += 1
            print(f"转换时发生未知错误: {filename}\n原因: {e}")
    
    # Formulate summary message
    summary_message = (
        f"批量转换完成！\n\n"
        f"  - 成功: {success_count} 个\n"
        f"  - 跳过: {skipped_count} 个\n"
        f"  - 失败: {failed_count} 个"
    )
    
    status = 'SUCCESS' if success_count > 0 else 'INFO'
    if failed_count > 0:
        status = 'WARNING'

    return (status, summary_message)

# The test block below will be removed as it's for development purposes.
# It will be replaced by an empty __main__ block for clarity.
if __name__ == '__main__':
    # This script is designed to be imported, not run directly.
    pass
