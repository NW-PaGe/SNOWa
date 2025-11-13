import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import geopandas as gpd
import seaborn as sns
import argparse

parser = argparse.ArgumentParser(description='This script adds site and lineage classification information to the full data set')
#parser.add_argument('data', help='The file to which site and lineage classification information is added.')
parser.add_argument("--dataset",
                    default="results/ww_data.csv",
                    help="The dataset")
parser.add_argument("--proportions",
                    default="results/population_weighted_props.csv")
parser.add_argument("--barplot",
                    default='results/proportions_barplot.jpeg')
parser.add_argument("--timeline",
                    default="results/timeline.jpeg")
parser.add_argument("--heatmap")
parser.add_argument("--n-weeks-map",
                    default="results/n_weeks_map.jpeg")
parser.add_argument("--top3",
                    default = "results/top3.jpeg")
args=parser.parse_args()

def pivot_to_table(weighted_proportions):
    """
    Pivot the weighted proportions into a wide format table:
    Rows = Week, Columns = Variants
    """
    pivot_table = weighted_proportions.pivot_table(
        index="Week", columns="variant", values="weighted_avg", fill_value=0
    )
    return pivot_table


def plot_barplot(pivot_table, full_df, output):
    """
    Plot a stacked bar chart of variant proportions by week using Freyja hex codes.

    Parameters:
    - pivot_table: result from pivot_to_table
    - df: original Freyja + lineage-merged DataFrame with 'variant' and 'hex_code'
    """
    # Build color mapping from df
    variant_colors = (
        full_df[["variant", "hex_code"]]
        .drop_duplicates()
        .set_index("variant")["hex_code"]
        .to_dict()
    )

    # Ensure color order matches the pivot_table column order
    colors = [variant_colors.get(v, "#999999") for v in pivot_table.columns]

    # Plot
    fig, ax = plt.subplots(figsize=(14, 10))
    pivot_table.plot(kind="bar", stacked=True, ax=ax, width=0.8, color=colors)
    ax.set_xlabel("Week of Sample Collection Date")
    ax.set_ylabel("Variant Population-Weighted Proportion")
    ax.set_title("Weekly Population-Weighted SARS-CoV-2 Variant Proportions")
    ax.set_xticks(range(len(pivot_table.index)))
    ax.set_xticklabels(pivot_table.index, rotation=90, fontsize=8)
    ax.legend(
        title="Variant",
        bbox_to_anchor=(0.5, -0.2),
        loc="upper center",
        ncol=min(10, len(pivot_table.columns)),
        fontsize=8,
    )
    plt.tight_layout(pad=2.0)
    plt.savefig(output)
    return fig

def plot_variant_presence_by_week(full_df, output, start_date='2024-01-01', end_date='2025-09-30'):
    """
    Plot weekly SARS-CoV-2 variant detection timeline using presence/absence,
    colored by hex code.

    Parameters:
    - df: DataFrame with columns ['Sample_Collection_Date', 'variant', 'hex_code']
    - start_date: Start date for the timeline (default '2024-01-01')
    - end_date: End date for the timeline (default '2025-09-30')
    """
    # Step 1: Extract week and filter time range
    full_df['Sample_Collection_Date'] = pd.to_datetime(full_df['Sample_Collection_Date'], errors='coerce')
    full_df = full_df[full_df['Sample_Collection_Date'].between(start_date, end_date)]
    full_df['Week'] = full_df['Sample_Collection_Date'].dt.strftime('%Y-W%U')

    # Step 2: Build week list
    weeks = pd.date_range(start=start_date, end=end_date, freq='W-MON')
    week_labels = [d.strftime('%Y-W%U') for d in weeks]

    # Step 3: Create variant-to-color map
    variant_colors = (
        full_df[['variant', 'hex_code']].drop_duplicates()
        .set_index('variant')['hex_code'].to_dict()
    )

    # Step 4: Build presence matrix
    presence = (
        full_df.groupby(['variant', 'Week'])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=week_labels, fill_value=0)
    )
    presence = (presence > 0).astype(int)

    # Step 5: Plot presence as color-coded squares
    fig, ax = plt.subplots(figsize=(16, 18))
    variants = presence.index.tolist()
    weeks_ordered = presence.columns.tolist()

    for row_idx, variant in enumerate(variants):
        for col_idx, week in enumerate(weeks_ordered):
            if presence.loc[variant, week] == 1:
                color = variant_colors.get(variant, "#555555")
                ax.scatter(col_idx, row_idx, color=color, s=100, marker='s')

    # Step 6: Format plot
    ax.set_xticks(range(len(weeks_ordered)))
    ax.set_xticklabels(weeks_ordered, rotation=90, fontsize=9)
    ax.set_xlim(-0.5, len(weeks_ordered) - 0.5)  # Add this line
    ax.set_yticks(range(len(variants)))
    ax.set_yticklabels(variants, fontsize=9)  # Reduce font size
    ax.set_ylim(-0.5, len(variants) - 0.5)
    ax.set_xlabel("Week")
    ax.set_ylabel("Variant")
    ax.set_title("Weekly Detection of SARS-CoV-2 Variants in Wastewater (Colored by Hex Code)")
    ax.grid(False)
    plt.tight_layout()
    plt.savefig(output)
    return fig

def create_filtered_heatmap(weighted_proportions, min_percent=10, num_weeks=8):
    # Copy and compute datetime version of week
    wpt = weighted_proportions.copy()
    wpt['Week_dt'] = pd.to_datetime(wpt['Week'] + '-1', format='%Y-W%U-%w')

    # Get last N weeks chronologically
    recent_weeks_df = (
        wpt[['Week', 'Week_dt']]
        .drop_duplicates()
        .sort_values('Week_dt')
        .tail(num_weeks)
    )
    recent_weeks = recent_weeks_df['Week'].tolist()
    recent_week_dates = recent_weeks_df.set_index('Week')['Week_dt'].to_dict()

    # Filter to recent weeks
    recent_data = wpt[wpt['Week'].isin(recent_weeks)]

    # Pivot table
    pivot = recent_data.pivot(index='variant', columns='Week', values='weighted_avg').fillna(0) * 100

    # Filter variants by 10% threshold
    filtered = pivot[pivot.max(axis=1) >= min_percent]

    # Rename columns to datetime-style week labels
    filtered.columns = [recent_week_dates[w].strftime('%Y-%m-%d') for w in filtered.columns]

    # Reorder columns
    filtered = filtered[sorted(filtered.columns)]

    # Plot
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        filtered,
        annot=True,
        fmt=".2g",
        cmap="Blues",
        cbar_kws={'label': 'Proportion (%)'}
    )
    plt.title('Variants ≥10% in Any Week (Past 8 Weeks)')
    plt.xlabel('Sample Collection Week')
    plt.ylabel('Variant')
    plt.savefig(args.heatmap)
    plt.tight_layout()

    return plt.gcf()

# weekly geo map of dominant variant trends
def plot_dominant_variant_maps_interactive(weighted_proportions, full_df, shapefile_path='defaults/WA_County_Boundaries.shp', weeks_back=12):
    """
    Generates weekly maps of the dominant SARS-CoV-2 variant in each WA county using weighted proportions.
    Skips weeks that have no usable data.
    """
    # Step 1: Load and normalize shapefile
    wa_shape = gpd.read_file(shapefile_path)
    wa_shape = wa_shape.rename(columns={"JURISDIC_3": "county"})
    wa_shape['county'] = wa_shape['county'].str.title()

    # Step 2: Merge proportions with county + hex info
    county_map = full_df[['Week', 'variant', 'county', 'hex_code']].drop_duplicates()
    proportions = weighted_proportions.merge(county_map, on=['Week', 'variant'], how='left')

    # Convert Week string to datetime for filtering and sorting
    proportions['Week_dt'] = pd.to_datetime(proportions['Week'] + '-1', format='%Y-W%U-%w')
    proportions = proportions[proportions['Week_dt'].notna()]

    # Step 3: Get the most recent `weeks_back` weeks with data
    recent_weeks_df = (
        proportions[['Week', 'Week_dt']]
        .drop_duplicates()
        .sort_values('Week_dt')
        .tail(weeks_back)
    )
    weeks_to_plot = []
    week_to_date = {}

    for _, row in recent_weeks_df.iterrows():
        week = row['Week']
        dt = row['Week_dt']
        if not proportions[proportions['Week'] == week].empty:
            weeks_to_plot.append(week)
            week_to_date[week] = dt

    if not weeks_to_plot:
        print("No usable weekly data available.")
        return

    # Step 4: Set up plots
    n = len(weeks_to_plot)
    rows = (n + 3) // 4
    cols = 4
    #fig, axes = plt.subplots(rows, cols, figsize=(cols * 6, rows * 6))
    #axes = axes.flatten()

    from matplotlib.gridspec import GridSpec

    fig = plt.figure(figsize=(cols * 6, rows * 6 + 2))  # +2 adds space for legend
    gs = GridSpec(rows + 1, cols, height_ratios=[1]*rows + [0.2])  # last row is for legend
    axes = [fig.add_subplot(gs[i, j]) for i in range(rows) for j in range(cols)]

    # creating a list for the variants to be included in the legend
    plotted_variants = []

    for i, week in enumerate(weeks_to_plot):
        ax = axes[i]
        print(f"Processing week: {week}")

        week_data = proportions[proportions['Week'] == week]
        if week_data.empty:
            print(f"  [SKIPPED] No data found for week {week}")
            continue

        # Group by county to get dominant variant
        county_aggregates = week_data.groupby(['county', 'variant']).agg({
            'weighted_avg': 'sum',
            'hex_code': 'first'
        }).reset_index()
        county_aggregates['normalized'] = county_aggregates.groupby('county')['weighted_avg'].transform(lambda x: x / x.sum())
        dominant = county_aggregates.loc[county_aggregates.groupby('county')['normalized'].idxmax()]

        # Merge with map
        map_df = wa_shape.merge(dominant[['county', 'variant', 'hex_code']], on='county', how='left')
        map_df['hex_code'] = map_df['hex_code'].fillna('#FFFFFF').astype(str)
        map_df['hex_code'] = map_df['hex_code'].where(map_df['hex_code'].str.startswith('#'), '#FFFFFF')

        #print(f"🧪 Plotting week: {week}")
        #print("Unique colors to be plotted:", map_df['hex_code'].unique())

        # Ensure column is string and fill anything invalid
        map_df['hex_code'] = map_df['hex_code'].astype(str).where(map_df['hex_code'].notna(), '#FFFFFF')
        map_df['hex_code'] = map_df['hex_code'].where(map_df['hex_code'].str.startswith('#'), '#FFFFFF')

        # appending variants to be included in legend in a list
        plotted_variants.append(map_df[['variant', 'hex_code']].dropna().drop_duplicates())

        # Final validation: only allow valid hex codes (#RGB or #RRGGBB)
        bad_rows = map_df[~map_df['hex_code'].str.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$')]
        if not bad_rows.empty:
            print("❌ Found invalid hex codes:")
            print(bad_rows[['county', 'variant', 'hex_code']])
            raise ValueError("Stopping: invalid RGBA values still present before plotting.")

        # Plot
        map_df.plot(ax=ax, color=map_df['hex_code'], edgecolor='black')

        #print(f"  Colors used for plotting: {map_df['hex_code'].unique()}")

        map_df.plot(ax=ax, color=map_df['hex_code'], edgecolor='black')
        title_date = pd.to_datetime(week_to_date[week])
        ax.set_title(f"Dominant Variant by County, Week of {title_date.strftime('%b %d, %Y')}", fontsize=16)
        ax.axis('off')

    if plotted_variants:
        legend_variants = pd.concat(plotted_variants).drop_duplicates().sort_values(by='variant')
    else:
        legend_variants = pd.DataFrame(columns=['variant', 'hex_code'])

    # Remove unused axes
    for ax in axes[len(weeks_to_plot):]:
        fig.delaxes(ax)

    # Only keep variants with valid hex codes
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=variant, markersize=10, markerfacecolor=hex_code)
        for variant, hex_code in zip(legend_variants['variant'], legend_variants['hex_code'])
        if isinstance(hex_code, str) and hex_code.startswith('#')
    ]

    # Add fallback legend for no-data areas
    legend_elements.append(
        Line2D([0], [0], marker='o', color='w', label='No Data', markersize=10, markerfacecolor='#FFFFFF')
        )

    legend_ax = fig.add_subplot(gs[-1, :])  # bottom row across all columns
    legend_ax.axis('off')  # hide the background

    legend = legend_ax.legend(
        handles=legend_elements,
        title="Variants",
        title_fontsize=18,
        loc='center',
        ncol=6,
        fontsize=14,
        markerscale=2,
        frameon=False
    )

    plt.tight_layout()
    plt.savefig(args.n_weeks_map, bbox_inches='tight')
    #print(map_df)
    return fig

def get_top_variants(weighted_proportions, num_weeks=8, top_n=3):
    df = weighted_proportions.copy()
    df['Week_dt'] = pd.to_datetime(df['Week'] + '-1', format='%Y-W%U-%w')

    recent_weeks_df = (
        df[['Week', 'Week_dt']]
        .drop_duplicates()
        .sort_values('Week_dt')
        .tail(num_weeks)
    )

    recent_weeks = recent_weeks_df['Week'].tolist()
    recent_data = df[df['Week'].isin(recent_weeks)]

    top_variants = (
        recent_data.groupby('variant')['weighted_avg']
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
        .index
        .tolist()
    )

    return top_variants, recent_weeks

def create_line_graph(weighted_proportions, top_variants, recent_weeks, df):
    # Filter to top variants and recent weeks only
    filtered = weighted_proportions[
        (weighted_proportions['variant'].isin(top_variants)) &
        (weighted_proportions['Week'].isin(recent_weeks))
    ]

    pivoted = filtered.pivot(index='Week', columns='variant', values='weighted_avg').fillna(0)
    pivoted.index = pd.to_datetime(pivoted.index + '-1', format='%Y-W%U-%w')

    variant_colors = df[['variant', 'hex_code']].drop_duplicates().set_index('variant')['hex_code'].to_dict()

    fig, ax = plt.subplots(figsize=(12, 8))
    for variant in top_variants:
        ax.plot(pivoted.index, pivoted[variant], label=variant, color=variant_colors.get(variant, 'black'))
        ax.text(
            pivoted.index[-1],
            pivoted[variant].iloc[-1],
            variant,
            fontsize=8,
            ha='left',
            va='center'
        )

    ax.set_title('Top 3 SARS-CoV-2 Variants in Wastewater (Past 8 Weeks)')
    ax.set_ylabel('Proportion')
    ax.set_xlabel('Week')
    ax.tick_params(axis='x', rotation=45)
    ax.legend(title='Variant', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig(args.top3)
    return fig

#Define the arguments
weighted_proportions=pd.read_csv(args.proportions)
full_df=pd.read_csv(args.dataset)
pivot_table = pivot_to_table(weighted_proportions)
barplot=args.barplot
timeline=args.timeline
n_weeks_map=args.n_weeks_map
top3 = args.top3

if args.barplot:
    plot_barplot(pivot_table, full_df, barplot)

if args.timeline:
    plot_variant_presence_by_week(full_df, timeline, start_date='2024-01-01', end_date='2025-09-30')

if args.heatmap:
    create_filtered_heatmap(weighted_proportions, min_percent=10, num_weeks=8)

if args.n_weeks_map:
    plot_dominant_variant_maps_interactive(weighted_proportions, full_df, shapefile_path='defaults/WA_County_Boundaries.shp', weeks_back=12)

if args.top3:
    top_variants, recent_weeks = get_top_variants(weighted_proportions, num_weeks=8, top_n=3)
    line_graph = create_line_graph(weighted_proportions, top_variants, recent_weeks, full_df)