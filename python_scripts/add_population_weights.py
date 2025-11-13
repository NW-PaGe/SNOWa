import argparse
import pandas as pd
parser = argparse.ArgumentParser(description='This script adds site and lineage classification information to the full data set')
parser.add_argument("input", help='The file to which site and lineage classification information is added.')
parser.add_argument("--output", "-o",
                    default="results/weighted_props.csv",
                    help="Specifies the output file")

args=parser.parse_args()

def calculate_weighted_variant_prevalence(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate population-weighted variant prevalence per week using raw summed proportions 
    divided by replicate count per site-week to get average proportions.
    """
    # Step 0: round population to whole number
    df['population'] = df['population'].round()
    #print(df)

    # Step 1: Unique sample metadata
    samples = df[['Lab_ID', 'Sample_Site', 'Week', 'population']].drop_duplicates()
    #print(samples)

    all_variants = df['variant'].unique()

    # Step 2: Full Lab_ID × variant grid
    full = samples.assign(key=1).merge(
        pd.DataFrame({'variant': all_variants, 'key': 1}), on='key'
    ).drop(columns='key')

    # Step 3: Merge in raw proportions
    df_key = df[['Lab_ID', 'variant', 'Variant_proportion']]
    full = full.merge(df_key, on=['Lab_ID', 'variant'], how='left')

    # Step 4: Fill missing variant proportions with 0
    full['Variant_proportion'] = full['Variant_proportion'].fillna(0)

    #  Step 5: Sum Variant_proportions per Sample_Site × Week × Variant
    summed_variant = (
        full.groupby(['Sample_Site', 'Week', 'variant'], as_index=False)
        .agg(sum_proportion=('Variant_proportion', 'sum'))
    )
    #print(summed_variant)

    #  Step 6: Count unique Lab_IDs per Sample_Site × Week
    sample_counts = (
        full[['Sample_Site', 'Week', 'Lab_ID']].drop_duplicates()
        .groupby(['Sample_Site', 'Week'], as_index=False)
        .agg(n_samples=('Lab_ID', 'count'))
    )
    #print(sample_counts)
    # Step 7: Merge in replicate counts
    summed_variant = summed_variant.merge(sample_counts, on=['Sample_Site', 'Week'], how='left')

    # Step 8: Compute avg_proportion = sum / n_samples
    summed_variant['avg_proportion'] = summed_variant['sum_proportion'] / summed_variant['n_samples']
    #print(summed_variant.head(20))

    # Step 9: Merge in population for weighting
    pop_lookup = samples[['Sample_Site', 'Week', 'population']].drop_duplicates()
    summed_variant = summed_variant.merge(pop_lookup, on=['Sample_Site', 'Week'], how='left')
    #print(summed_variant)

    # Step 10: Compute weighted sum = avg_proportion × population
    summed_variant['weighted_sum'] = summed_variant['avg_proportion'] * summed_variant['population']
    #print(summed_variant)

    # Step 11: Aggregate weighted sums per Week × Variant
    weekly_variant_weights = (
        summed_variant.groupby(['Week', 'variant'], as_index=False)['weighted_sum'].sum()
    )
    #print(weekly_variant_weights)

    # Step 12: Compute total population per week (each site counted once per week)
    total_population = (
        samples[['Week', 'Sample_Site', 'population']]
        .drop_duplicates(subset=['Week', 'Sample_Site'])  #  ensures one row per site per week
        .groupby('Week', as_index=False)['population']
        .sum()
        .rename(columns={'population': 'total_population'})
    )

    #print(total_population)
    # Step 13: Merge + calculate weighted average
    result = weekly_variant_weights.merge(total_population, on='Week', how='left')
    result['weighted_avg'] = result['weighted_sum'] / result['total_population']

    return result.sort_values(['Week', 'variant']).reset_index(drop=True)[['Week', 'variant', 'weighted_avg', 'total_population']]

full_df = pd.read_csv(args.input)
weighted_proportions = calculate_weighted_variant_prevalence(full_df)
#writing this out to see if props drop below 1 toward the newer samples
weighted_proportions.to_csv(args.output, index=False)
#eliminate lab_ID going forward

