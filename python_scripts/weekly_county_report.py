import pandas as pd
import argparse

# QC Check for County Proportions - Weekly Breakdown by County for Comparison with the Weekly Maps of Dominant Variants by County
def weekly_county_props_report(weekly_maps_plt_filtered):
    """
    Show variant breakdown for each county for all weeks.

    Parameters:
    -----------
    weekly_maps_plt_filtered : DataFrame
        Output from filter_by_timeframe()

    Returns:
    --------
    None (prints detailed breakdown)
    """
    df = weekly_maps_plt_filtered

    # Get all weeks, sorted chronologically
    all_weeks = df['Week'].drop_duplicates().sort_values().tolist()

    # Drop 0% variants
    df = df[df['weighted_avg'] > 0]

    print("="*100)
    print("COUNTY-LEVEL VARIANT BREAKDOWN - ALL WEEKS")
    print("="*100)

    # Sort by week then county
    df = df.sort_values(['Week', 'county'])

    for week in all_weeks:
        # Week is already in datetime format (yyyy-mm-dd), so just format it
        monday_date = pd.to_datetime(week).strftime('%B %d, %Y')
        print(f"\n{'='*100}")
        print(f"WEEK OF: {monday_date}")
        print(f"{'='*100}")

        week_data = df[df['Week'] == week]
        if week_data.empty:
            print("   No data for this week\n")
            continue

        counties = sorted(week_data['county'].unique())
        for county in counties:
            county_data = week_data[week_data['county'] == county].sort_values('weighted_avg', ascending=False)
            print(f"\n{county}:")
            print(f"   {'Variant':<20} {'Percentage':>12}")
            print(f"   {'-'*20} {'-'*12}")
            total = 0
            for _, row in county_data.iterrows():
                pct = row['weighted_avg'] * 100
                total += pct
                print(f"   {row['variant']:<20} {pct:>11.2f}%")
            print(f"   {'-'*20} {'-'*12}")
            print(f"   {'TOTAL':<20} {total:>11.2f}%")

    print(f"\n{'='*100}")
    print("END REPORT")
    print(f"{'='*100}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='This script adds site and lineage classification information to the full data set')
    parser.add_argument("--input", "-i", required=True, help='Path to weekly maps plt dataset CSV')
    args=parser.parse_args()
    weekly_maps_plt_filtered = pd.read_csv(args.input)
    weekly_county_props_report(weekly_maps_plt_filtered)