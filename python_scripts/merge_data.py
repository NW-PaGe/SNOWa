import os
import pandas as pd
def process_data():
    # 1 Combine all data files into one master file
    # Set the directory containing the CSV files
    folder_path = 'runs/'
    # List all CSV files in the folder
    csv_files = [f for f in os.listdir(folder_path) if f.endswith('.tsv')]
    # Read and concatenate all CSV files
    dataframes = []
    for file in csv_files:
        file_path = os.path.join(folder_path, file)
        df = pd.read_csv(file_path, sep='\t')
        # Optional: set Lab_ID as index if needed
        if 'Lab_ID' in df.columns:
            df.set_index('Lab_ID', inplace=False)  # Change to inplace=True if you want to modify df directly
        dataframes.append(df)
    # Concatenate all DataFrames
    combined_df = pd.concat(dataframes, ignore_index=True)
    df = pd.DataFrame(combined_df)
    # Save the result
    combined_df.to_csv('results/combined_output.csv', index=False)
    print("Concatenation complete. Output saved as 'combined_output.csv'.")

    return combined_df, df

# Run the QC data combination
combined_df, df = process_data()