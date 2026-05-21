# 2  Add sample site and lineage classifications file
# adding sample site locations and lineage classifications

import pandas as pd
import argparse

def map_metadata(sites, classifications, input, output):
    """
    Add sample site locations and lineage classifications to combined dataframe.

    """

    # Load metadata files
    try:
        lineage_classifications = pd.read_csv(classifications)
    except FileNotFoundError:
        raise FileNotFoundError(f"Lineage classifications file not found: {classifications}")

    try:
        sample_sites = pd.read_csv(sites)
    except FileNotFoundError:
        raise FileNotFoundError(f"Sample sites file not found: {sites}")

    try:
        combined_df = pd.read_csv(input)
    except FileNotFoundError:
        raise FileNotFoundError(f"Data file not found: {input}")

    # Working with dates
    # Set to datetime
    combined_df['Sample_Collection_Date'] = pd.to_datetime(combined_df['Sample_Collection_Date'])

    # Get the Monday of each week in yyyy-mm-dd format
    combined_df['Week'] = combined_df['Sample_Collection_Date'].dt.to_period('W-MON').dt.start_time.dt.date

    # Convert Week column from string to datetime
    combined_df['Week'] = pd.to_datetime(combined_df['Week'])

    # Add lineages
    # Merge with lineage classifications to add parent lineage and hex code
    full_df = combined_df.merge(
        lineage_classifications[['wastewater_variant_name', 'lineage_extracted', 'hex_code']], 
        how='left', 
        left_on='Variant_name', 
        right_on='lineage_extracted'
    ).rename(columns={'wastewater_variant_name': 'variant'})  # Rename for clarity

    # Add sample sites
    full_df = full_df.merge(
        sample_sites[['Sample_Site', 'county', 'population']],
        how='left', 
        on='Sample_Site'
    )

    full_df['population'] = full_df['population'].round()

    # Check for duplicate rows for same Sample_ID and variant
    duplicates = full_df[full_df.duplicated(subset=['Sample_ID', 'variant'], keep=False)]
    if not duplicates.empty:
        print(f"⚠️  Warning: Found {len(duplicates)} duplicate rows for same Sample_ID and variant")

    # Drop validation data
    full_df = full_df[~full_df['Lab_ID'].str.contains('WWVal|positive|negative|control', case=False, na=False)]

    # Save the result
    full_df.to_csv(output, index=False)
    print("✅ Mapping complete. Results saved as " + args.output)

    return full_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sites", "-s", required=True, help="Path to Sample Sites csv")
    parser.add_argument("--classifications", "-c", required=True, help="Path to lineage classifications csv file")
    parser.add_argument("--input", "-i", required=True, help="Path to deduplicated data")
    parser.add_argument("--output", "-o", required=True, help="Path to output file")
    args = parser.parse_args()

    map_metadata(args.sites, args.classifications, args.input, args.output)
