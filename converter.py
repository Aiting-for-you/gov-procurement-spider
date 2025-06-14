import pandas as pd
import os
import glob

def convert_csv_to_excel(csv_file_path: str):
    """
    Converts a single CSV file to an Excel file (.xlsx).

    The Excel file will be saved in the same directory as the CSV file,
    with the same name but a .xlsx extension.

    Args:
        csv_file_path (str): The full path to the input CSV file.
    """
    try:
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')
        excel_file_path = os.path.splitext(csv_file_path)[0] + '.xlsx'
        df.to_excel(excel_file_path, index=False, engine='openpyxl')
        print(f"Successfully converted '{os.path.basename(csv_file_path)}' to '{os.path.basename(excel_file_path)}'")
        return True
    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
        return False
    except Exception as e:
        print(f"An error occurred while converting '{csv_file_path}': {e}")
        return False

def main(target_directory: str = 'output'):
    """
    Scans the specified directory for all .csv files and converts them to .xlsx.
    
    Args:
        target_directory (str): The directory to scan for CSV files. Defaults to 'output'.
    """
    print(f"Scanning for CSV files in '{target_directory}' directory...")

    if not os.path.isdir(target_directory):
        print(f"Error: The directory '{target_directory}' does not exist.")
        return False

    csv_files = glob.glob(os.path.join(target_directory, '*.csv'))

    if not csv_files:
        print("No CSV files found to convert.")
        return False

    conversion_results = [convert_csv_to_excel(csv_file) for csv_file in csv_files]

    print("\nConversion process finished.")
    return all(conversion_results)

if __name__ == "__main__":
    main()
