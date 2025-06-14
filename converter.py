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
        # Read the CSV file. It's important to use 'utf-8-sig' to handle the BOM
        # that Excel adds when saving UTF-8 CSVs.
        df = pd.read_csv(csv_file_path, encoding='utf-8-sig')

        # Define the output Excel file path
        excel_file_path = os.path.splitext(csv_file_path)[0] + '.xlsx'

        # Convert to Excel, without writing the pandas index column
        df.to_excel(excel_file_path, index=False, engine='openpyxl')
        
        print(f"Successfully converted '{os.path.basename(csv_file_path)}' to '{os.path.basename(excel_file_path)}'")

    except FileNotFoundError:
        print(f"Error: The file '{csv_file_path}' was not found.")
    except Exception as e:
        print(f"An error occurred while converting '{csv_file_path}': {e}")


def main():
    """
    Scans the 'output' directory for all .csv files and converts them to .xlsx.
    """
    output_dir = 'output'
    print(f"Scanning for CSV files in '{output_dir}' directory...")

    if not os.path.isdir(output_dir):
        print(f"Error: The directory '{output_dir}' does not exist. Please run the crawler first to generate CSV files.")
        return

    # Find all CSV files in the output directory
    csv_files = glob.glob(os.path.join(output_dir, '*.csv'))

    if not csv_files:
        print("No CSV files found to convert.")
        return

    for csv_file in csv_files:
        convert_csv_to_excel(csv_file)

    print("\nConversion process finished.")


if __name__ == "__main__":
    # Ensure you have the necessary packages installed:
    # pip install pandas openpyxl
    main()
