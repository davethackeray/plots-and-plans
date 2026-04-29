import pandas as pd
from pathlib import Path

file_path = Path('../OddLot_Agent_Tracker_V4.xlsx')
try:
    df = pd.read_excel(file_path)
    print(f"File: {file_path.name}")
    print(f"Total Rows: {len(df)}")
    print(f"Columns: {list(df.columns)}")
    print("\nFirst 3 Rows (Sample Data):")
    print(df.head(3).to_markdown())
except Exception as e:
    print(f"Error reading file: {e}")
