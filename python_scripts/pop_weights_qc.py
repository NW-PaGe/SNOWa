import pandas as pd
import argparse
from pathlib import Path


def post_weighting_qc(weighted_proportions, county_proportions, output_txt):
    """
    Post-Weighting Quality Control for variant proportion data

    Parameters:
    -----------
    weighted_proportions : pandas DataFrame
        DataFrame with columns: Week, variant, weighted_avg, total_population
    county_proportions : pandas DataFrame
        DataFrame with county-level proportions
    output_txt : str
        Path to write the QC log file

    Returns:
    --------
    dict
        Summary dictionary with QC metrics
    """

    # Log capture — print() gets swallowed by Snakemake; capture to log_lines
    # and write to output_txt at the end so it persists as a file.
    log_lines = []
    def log(msg=""):
        print(msg)
        log_lines.append(msg)

    Path(output_txt).parent.mkdir(parents=True, exist_ok=True)

    log("=== POST-WEIGHTING QC REPORT ===\n")

    # 1. Validate weighting calculations
    log("1. POPULATION WEIGHTING VALIDATION:")

    # Check that weighted proportions sum appropriately per week
    weekly_sums = weighted_proportions.groupby('Week')['weighted_avg'].sum()
    log(f"   Weekly proportion sums - Range: {weekly_sums.min():.3f} to {weekly_sums.max():.3f}")

    # Flag weeks where sums are far from 1.0
    unusual_sums = weekly_sums[(weekly_sums < 0.8) | (weekly_sums > 1.2)]
    if len(unusual_sums) > 0:
        log(f"   ⚠️  {len(unusual_sums)} weeks have unusual sum totals:")
        for qc_week, qc_sum_val in unusual_sums.items():
            log(f"      - {qc_week}: {qc_sum_val:.3f}")
    else:
        log("   ✅ All weekly sums are within reasonable range (0.8-1.2)")

    # Check population coverage consistency
    pop_by_week = weighted_proportions.groupby('Week')['total_population'].first()
    pop_variation = pop_by_week.std() / pop_by_week.mean() * 100
    log(f"   Population coverage variation: {pop_variation:.1f}% CV")
    log(f"   Population range: {pop_by_week.min():,.0f} to {pop_by_week.max():,.0f}")

    if pop_variation > 20:
        log("   ⚠️  High population variation between weeks (>20% CV)")
    else:
        log("   ✅ Population coverage is consistent across weeks")

    # 2. Check for anomalous values post-weighting
    log("\n2. ANOMALOUS VALUES CHECK:")

    # Check for extreme proportions
    max_prop = weighted_proportions['weighted_avg'].max()
    min_prop = weighted_proportions['weighted_avg'].min()
    log(f"   Weighted proportion range: {min_prop:.4f} to {max_prop:.4f}")

    # Flag variants with unusually high single-week proportions
    qc_high_props = weighted_proportions[weighted_proportions['weighted_avg'] > 0.8]
    if len(qc_high_props) > 0:
        log(f"   ⚠️  {len(qc_high_props)} variant-week combinations >80%:")
        for _, qc_row in qc_high_props.iterrows():
            log(f"      - {qc_row['variant']} in {qc_row['Week']}: {qc_row['weighted_avg']:.3f}")

    # Check for negative values (shouldn't happen but good to verify)
    qc_negative_props = weighted_proportions[weighted_proportions['weighted_avg'] < 0]
    if len(qc_negative_props) > 0:
        log(f"   ❌ {len(qc_negative_props)} negative weighted proportions found!")
    else:
        log("   ✅ No negative weighted proportions")

    # 3. Validate temporal trends consistency
    log("\n3. TEMPORAL CONSISTENCY CHECK:")

    # Check for sudden appearance/disappearance of variants
    variant_weeks = weighted_proportions.groupby('variant').agg({
        'Week': ['count', 'min', 'max'],
        'weighted_avg': ['mean', 'std', 'max']
    }).round(4)
    variant_weeks.columns = ['week_count', 'first_week', 'last_week', 'mean_prop', 'std_prop', 'max_prop']

    # Find variants that appear in very few weeks but with high proportions
    sporadic_variants = variant_weeks[
        (variant_weeks['week_count'] <= 3) & 
        (variant_weeks['max_prop'] > 0.1)
    ]

    if len(sporadic_variants) > 0:
        log(f"   ⚠️  {len(sporadic_variants)} variants appear sporadically but with high proportions:")
        for qc_variant, qc_data in sporadic_variants.iterrows():
            log(f"      - {qc_variant}: {qc_data['week_count']} weeks, max {qc_data['max_prop']:.3f}")
    else:
        log("   ✅ No sporadic high-proportion variants detected")

    # Check for variants with high variability
    high_variability = variant_weeks[
        (variant_weeks['std_prop'] > 0.1) & 
        (variant_weeks['mean_prop'] > 0.05)
    ]

    if len(high_variability) > 0:
        log(f"   ⚠️  {len(high_variability)} variants show high week-to-week variability:")
        for qc_variant2, qc_data2 in high_variability.head(5).iterrows():
            log(f"      - {qc_variant2}: mean={qc_data2['mean_prop']:.3f}, std={qc_data2['std_prop']:.3f}")

    # 4. Assess regional distribution patterns
    log("\n4. REGIONAL DISTRIBUTION CHECK:")

    try:
        # Check county coverage
        counties_per_week = county_proportions.groupby('Week')['county'].nunique()
        log(f"   County coverage per week: {counties_per_week.min()} to {counties_per_week.max()} counties")

        total_counties = county_proportions['county'].nunique()
        log(f"   Total counties with data: {total_counties}")

        # Check for counties with very limited data
        county_weeks = county_proportions.groupby('county')['Week'].nunique()
        limited_counties = county_weeks[county_weeks <= 2]

        if len(limited_counties) > 0:
            log(f"   ⚠️  {len(limited_counties)} counties have ≤2 weeks of data:")
            for qc_county, qc_weeks in limited_counties.items():
                log(f"      - {qc_county}: {qc_weeks} weeks")

        # Check for extreme county-level proportions
        county_max = county_proportions['weighted_avg'].max()
        county_min = county_proportions['weighted_avg'].min()
        log(f"   County-level proportion range: {county_min:.4f} to {county_max:.4f}")

        extreme_county_props = county_proportions[county_proportions['weighted_avg'] > 0.9]
        if len(extreme_county_props) > 0:
            log(f"   ⚠️  {len(extreme_county_props)} county-variant-week combinations >90%")
    except:
        log("   ⚠️  County-level data not provided - skipping regional analysis")

    # 5. Data completeness check
    log("\n5. DATA COMPLETENESS:")

    # Check weeks with limited variant diversity
    variants_per_week = weighted_proportions.groupby('Week').agg({
        'variant': 'nunique',
        'weighted_avg': 'sum'
    }).round(3)
    variants_per_week.columns = ['variant_count', 'total_proportion']

    low_diversity_weeks = variants_per_week[variants_per_week['variant_count'] <= 2]
    if len(low_diversity_weeks) > 0:
        log(f"   ⚠️  {len(low_diversity_weeks)} weeks have ≤2 variants detected:")
        for qc_week_check, qc_data_check in low_diversity_weeks.iterrows():
            log(f"      - {qc_week_check}: {qc_data_check['variant_count']} variants")
    else:
        log("   ✅ All weeks have >2 variants detected")

    # Check for weeks with very low total proportions
    low_prop_weeks = variants_per_week[variants_per_week['total_proportion'] < 0.7]
    if len(low_prop_weeks) > 0:
        log(f"   ⚠️  {len(low_prop_weeks)} weeks have total proportions <70%:")
        for qc_week_prop, qc_data_prop in low_prop_weeks.iterrows():
            log(f"      - {qc_week_prop}: {qc_data_prop['total_proportion']:.3f}")

    # 6. Summary statistics
    log("\n6. SUMMARY STATISTICS:")
    log(f"   Total weeks analyzed: {weighted_proportions['Week'].nunique()}")
    log(f"   Total variants detected: {weighted_proportions['variant'].nunique()}")
    log(f"   Total variant-week combinations: {len(weighted_proportions)}")
    log(f"   Average variants per week: {weighted_proportions.groupby('Week')['variant'].nunique().mean():.1f}")
    log(f"   Average population coverage: {weighted_proportions['total_population'].mean():,.0f}")

    log("\n=== END QC REPORT ===")

    Path(output_txt).write_text("\n".join(log_lines))
    log(f"\n💾 Saved QC log to {output_txt}")

    qc_summary = {
        'weeks_analyzed': weighted_proportions['Week'].nunique(),
        'variants_detected': weighted_proportions['variant'].nunique(),
        'avg_variants_per_week': weighted_proportions.groupby('Week')['variant'].nunique().mean(),
        'population_coverage_range': (pop_by_week.min(), pop_by_week.max()),
        'proportion_range': (min_prop, max_prop),
        'unusual_sum_weeks': len(unusual_sums),
        'high_proportion_combinations': len(qc_high_props),
        'negative_proportions': len(qc_negative_props),
        'sporadic_variants': len(sporadic_variants),
        'high_variability_variants': len(high_variability),
        'low_diversity_weeks': len(low_diversity_weeks)
    }

    return qc_summary


def check_sums(weighted_proportions, county_proportions):
    """
    Post-Weighting Quality Control for variant proportion data: Sums Checks Equal 1

    Parameters:
    -----------
    weighted_proportions : pandas DataFrame
        DataFrame with columns: Week, variant, weighted_avg, total_population
    county_proportions : pandas DataFrame
        DataFrame with county-level proportions

    Returns:
    --------
    check_sums_statewide.csv: output file
        Contains table of statewide weekly sums of variant proportion estimates
    check_sums_counties.csv: output file
        Contains table of weekly sums of variant proportion estimates by county
    Sums should be near or close to 1 and not over
    """

    # check sums of statewide population weights
    check_sums_statewide = weighted_proportions.groupby('Week')['weighted_avg'].sum()
    check_sums_statewide.to_csv("results/qc_check_sums_statewide.csv")

    # check sums of county population weights
    check_sums_counties = county_proportions.groupby(['Week', 'county'])['weighted_avg'].sum()
    check_sums_counties.to_csv("results/qc/check_sums_counties.csv")

    return check_sums_statewide, check_sums_counties


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='This script performs quality control on the population-weighted variant proportions.')
    parser.add_argument("--county", "-c", required=True, help='County-weighted proportions file in .csv format')
    parser.add_argument("--state", "-s", required=True, help='State-weighted proportions file in .csv format')
    parser.add_argument("--output-txt", "-o", required=True, help="Path for QC log output (.txt)")
    args = parser.parse_args()

    weighted_proportions = pd.read_csv(args.state)
    county_proportions = pd.read_csv(args.county)

    post_weighting_qc_results = post_weighting_qc(weighted_proportions, county_proportions, args.output_txt)
    check_sums(weighted_proportions, county_proportions)

    print("💾 Post-weighting QC - Sums Check completed. Results saved to results/qc/check_sums_*.csv")