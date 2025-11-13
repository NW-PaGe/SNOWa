# County
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description='This script adds site and lineage classification information to the full data set')
parser.add_argument("input", help='The file to which county-weighted proportions are added.')
parser.add_argument("--output", "-o",
                    default="results/county_weighted_props.csv",
                    help="Specifies the output file")

args=parser.parse_args()

def calculate_county_weighted_variant_prevalence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate population-weighted variant prevalence per week per county.
    """
    df['population'] = df['population'].round()

    # Step 1: Sample metadata (assuming Sample_Site can be mapped to county)
    samples = df[['Lab_ID', 'Sample_Site', 'Week', 'population', 'county']].drop_duplicates()

    all_variants = df['variant'].unique()

    # Step 2: Full grid of Lab_ID × variant
    full = samples.assign(key=1).merge(
        pd.DataFrame({'variant': all_variants, 'key': 1}), on='key'
    ).drop(columns='key')

    # Step 3: Merge in variant proportions
    df_key = df[['Lab_ID', 'variant', 'Variant_proportion']]
    full = full.merge(df_key, on=['Lab_ID', 'variant'], how='left')
    full['Variant_proportion'] = full['Variant_proportion'].fillna(0)

    # Step 4: Sum proportions at Sample_Site × Week × Variant
    summed_variant = (
        full.groupby(['Sample_Site', 'Week', 'variant'], as_index=False)
        .agg(sum_proportion=('Variant_proportion', 'sum'))
    )

    # Step 5: Count replicates per Sample_Site × Week
    sample_counts = (
        full[['Sample_Site', 'Week', 'Lab_ID']].drop_duplicates()
        .groupby(['Sample_Site', 'Week'], as_index=False)
        .agg(n_samples=('Lab_ID', 'count'))
    )
    summed_variant = summed_variant.merge(sample_counts, on=['Sample_Site', 'Week'], how='left')

    # Step 6: Compute avg proportion
    summed_variant['avg_proportion'] = summed_variant['sum_proportion'] / summed_variant['n_samples']

    # Step 7: Merge in population and county
    pop_lookup = samples[['Sample_Site', 'Week', 'population', 'county']].drop_duplicates()
    summed_variant = summed_variant.merge(pop_lookup, on=['Sample_Site', 'Week'], how='left')

    # Step 8: Compute weighted sum
    summed_variant['weighted_sum'] = summed_variant['avg_proportion'] * summed_variant['population']

    # Step 9: Aggregate per Week × County × Variant
    county_variant_weights = (
        summed_variant.groupby(['Week', 'county', 'variant'], as_index=False)['weighted_sum'].sum()
    )

    # Step 10: Total population per Week × County
    total_population = (
        pop_lookup.drop_duplicates(subset=['Week', 'Sample_Site'])
        .groupby(['Week', 'county'], as_index=False)['population']
        .sum()
        .rename(columns={'population': 'total_population'})
    )

    # Step 11: Merge and compute final weighted average
    result = county_variant_weights.merge(total_population, on=['Week', 'county'], how='left')
    result['weighted_avg'] = result['weighted_sum'] / result['total_population']

    # Step 12: Enrich with hex_code
    hex_lookup = df[['variant', 'hex_code']].drop_duplicates()
    result = result.merge(hex_lookup, on='variant', how='left')

    return result.sort_values(['Week', 'county', 'variant']).reset_index(drop=True)[
        ['Week', 'county', 'variant', 'weighted_sum', 'total_population', 'weighted_avg', 'hex_code']
    ]

full_df = pd.read_csv(args.input)
county_df = calculate_county_weighted_variant_prevalence(full_df)
county_df.to_csv(args.output, index=False)