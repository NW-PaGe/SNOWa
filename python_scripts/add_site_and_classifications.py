# 2  Add sample site and lineage classifications file
# adding sample site locations and lineage classifications

import pandas as pd
import argparse

parser = argparse.ArgumentParser(description='This script adds site and lineage classification information to the full data set')
#parser.add_argument('data', help='The file to which site and lineage classification information is added.')
parser.add_argument("--output", "-o",
                    default="results/ww_data.csv",
                    help="Specifies the output file")

args=parser.parse_args()

classifications = "defaults/ww_lineage_classifications.csv"
sites = "defaults/sample_site-counties.csv"
combined_df = "results/combined_output.csv"

lineage_classifications = pd.read_csv(classifications)
sample_sites = pd.read_csv(sites)
combined_df = pd.read_csv(combined_df)

# Working with dates
# set to datetime
combined_df['Sample_Collection_Date'] = pd.to_datetime(combined_df['Sample_Collection_Date'])

combined_df['Week'] = combined_df['Sample_Collection_Date'].dt.strftime('%Y-W%U')

# add lineages
# Merge with lineage classifications to add parent lineage and hex code
full_df = combined_df.merge(lineage_classifications[['wastewater_variant_name', 'lineage_extracted', 'hex_code']], 
                    how='left', left_on='Variant_name', right_on='lineage_extracted'
                    ).rename(columns={'wastewater_variant_name': 'variant'})  # Rename for clarity

# add sample sites
full_df = full_df.merge(
    sample_sites[['Sample_Site', 'county', 'latitude', 'longitude', 'population']],
    how='left', on='Sample_Site'
    )

full_df['population'] = full_df['population'].round()

full_df = full_df[full_df['Week'] >= '2024-W01']

# Check for duplicate rows for same Sample_ID and variant
full_df[full_df.duplicated(subset=['Sample_ID', 'variant'], keep=False)]

# drop validation data
full_df = full_df[~full_df['Lab_ID'].str.contains('WWVal', na=False)]

# Save the result
full_df.to_csv(args.output, index=False)
print("Mapping complete. Results saved as " + args.output)