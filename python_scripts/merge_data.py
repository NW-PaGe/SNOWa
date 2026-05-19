import os
import pandas as pd
import argparse

def process_data(directory):
    """
    Merge data files into one master file.
    """
    # 1 Combine all data files into one master file

    # List all CSV files in the folder
    csv_files = [f for f in os.listdir(directory) if f.endswith('.tsv')] # uncomment after testing

    # Read and concatenate all CSV files
    dataframes = []
    for file in csv_files:
        file_path = os.path.join(directory, file)
        df = pd.read_csv(file_path, sep='\t') 

        # Add source file column for data provenance
        df['source_file'] = file  # Keep full filename like 'ww_batch_output_221.tsv'
        # Or if you want just the batch number:
        # df['source_file'] = file.replace('ww_batch_output_', '').replace('.tsv', '')

        # Optional: set Lab_ID as index if needed
        if 'Lab_ID' in df.columns:
            df.set_index('Lab_ID', inplace=False)  # Change to inplace=True if you want to modify df directly
        dataframes.append(df)

    # Concatenate all DataFrames
    raw_combined_df = pd.concat(dataframes, ignore_index=True)
    df = pd.DataFrame(raw_combined_df)
    # Save the result
    raw_combined_df.to_csv('results/raw_combined_output.csv', index=False)
    print("Concatenation complete. Output saved as 'combined_output.csv'.")

    return raw_combined_df, df

# Run the QC data combination
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory")
    parser.add_argument("--output")
    args = parser.parse_args()
    directory = args.directory
    raw_combined_df, df = process_data(directory)