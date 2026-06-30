import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import matplotlib.gridspec as gridspec
import matplotlib.colors as mcolors
import geopandas as gpd
import seaborn as sns
import altair as alt
import argparse

##############################################################################

# PLOT STACKED BAR PLOT
def pivot_to_table(df_stacked_bar):
    """
    Pivot the weighted proportions into a wide format table:
    Rows = Week, Columns = Variants
    """
    pivot_table = df_stacked_bar.pivot_table(
        index="Week", columns="variant", values="weighted_avg", fill_value=0
    )
    return pivot_table

def plot_figure(pivot_table, df_stacked_bar):
    """
    Plot a stacked bar chart of variant proportions by week using Freyja hex codes,
    with a table showing the most recent week's proportions on the side.

    Parameters:
    - pivot_table: result from pivot_to_table
    - full_df: original Freyja + lineage-merged DataFrame with 'variant' and 'hex_code'
    """
    # Build color mapping from df
    variant_colors = (
        df_stacked_bar[["variant", "hex_code"]]
        .drop_duplicates()
        .set_index("variant")["hex_code"]
        .to_dict()
    )
    # Ensure color order matches the pivot_table column order
    colors = [variant_colors.get(v, "#999999") for v in pivot_table.columns]

    # Format dates for x-axis labels
    def week_to_date(week):
        """Convert Week to string format YYYY-MM-DD for display."""
        return pd.to_datetime(week).strftime('%Y-%m-%d')

    date_labels = [week_to_date(week) for week in pivot_table.index]

    # Get most recent week's data and filter out variants below threshold
    most_recent_week = pivot_table.index[-1]
    recent_data = pivot_table.iloc[-1]

    # Filter to only include variants with proportion >= 0.001 (0.1%)
    threshold = 0.001
    recent_data_filtered = recent_data[recent_data >= threshold].sort_values(ascending=False)

    # Create figure with GridSpec for custom layout - much larger overall size
    fig = plt.figure(figsize=(32, 14))
    gs = gridspec.GridSpec(1, 2, width_ratios=[4, 1], wspace=0.25)

    # debugging nan color error
    print(pivot_table.columns)

    # Main plot on the left - larger
    ax_main = fig.add_subplot(gs[0])
    pivot_table.plot(kind="bar", stacked=True, 
                     ax=ax_main, width=1.00, color=colors,         
                     edgecolor='white',  # Add white borders between bars
                     linewidth=0.5)       # Border width)
    ax_main.set_xlabel("Week of Sample Collection Date", fontsize=12)
    ax_main.set_ylabel("Variant Population-Weighted Proportion", fontsize=12)
    ax_main.set_title("Weekly Population-Weighted SARS-CoV-2 Variant Proportions Across All Sampling Sites, Washington State", 
                     fontsize=13, pad=20)
    ax_main.set_xticks(range(len(pivot_table.index)))
    ax_main.set_xticklabels(date_labels, rotation=90, fontsize=12)
    ax_main.legend(
        title="Variant",
        bbox_to_anchor=(0.5, -0.15),
        loc="upper center",
        ncol=min(12, len(pivot_table.columns)),
        fontsize=12,
    )

    # Table on the right
    ax_table = fig.add_subplot(gs[1])
    ax_table.axis('off')

    # Add title for table
    ax_table.text(0.5, 0.98, f'Most Recent Week\n{week_to_date(most_recent_week)}', 
                 ha='center', va='top', fontsize=12, weight='bold',
                 transform=ax_table.transAxes)



    # Prepare table data (only variants >= 0.1%)
    table_data = []
    for variant, proportion in recent_data_filtered.items():
        percentage = f"{proportion * 100:.1f}%"
        table_data.append([variant, percentage])

    # Create table
    if len(table_data) > 0:
        table = ax_table.table(
            cellText=table_data,
            colLabels=['Variant', 'Proportion'],
            cellLoc='left',
            loc='upper center',
            bbox=[0, 0.05, 1, 0.85]
        )

        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(14)
        table.scale(1, 2.2)

        # Color code the variant cells
        for i, (variant, _) in enumerate(table_data):
            cell = table[(i+1, 0)]  # +1 to skip header row
            cell.set_facecolor(variant_colors.get(variant, "#999999"))
            cell.set_text_props(weight='bold', color='white')

        # Style header
        for i in range(2):
            table[(0, i)].set_facecolor('#4472C4')
            table[(0, i)].set_text_props(weight='bold', color='white')


    plt.tight_layout()
    plt.savefig("results/proportions_plot.jpeg", dpi=300, bbox_inches='tight')
    return fig



##############################################################################

# PRESENCE/ABSENCE QA PLOT

def plot_variant_presence_by_week(df):
    """
    Plot weekly SARS-CoV-2 variant detection timeline using presence/absence,
    colored by hex code.
    Parameters:
    - df: DataFrame with columns ['Week', 'variant', 'hex_code', 'weighted_avg']
    """

    # Step 1: Filter to only rows where variant was actually detected
    df_detected = df[df['weighted_avg'] > 0].copy()

    # Step 2: Get all unique weeks from the original data (for the full timeline)
    week_labels = sorted(df['Week'].unique())

    # Step 3: Create variant-to-color map
    variant_colors = (
        df[['variant', 'hex_code']].drop_duplicates()
        .set_index('variant')['hex_code'].to_dict()
    )

    # Step 4: Build presence matrix (now only from detected variants)
    presence = (
        df_detected.groupby(['variant', 'Week'])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=week_labels, fill_value=0)
    )
    presence = (presence > 0).astype(int)

    # Sort variants by first week of appearance
    first_appearance = presence.idxmax(axis=1)
    presence = presence.loc[first_appearance.sort_values(ascending=False).index]

    # Step 5: Format dates for x-axis labels
    def week_to_date(week):
        """Convert Week to string format YYYY-MM-DD for display."""
        return pd.to_datetime(week).strftime('%Y-%m-%d')
    date_labels = [week_to_date(week) for week in week_labels]

    # Step 6: Plot presence as color-coded squares
    fig, ax = plt.subplots(figsize=(16, 18))
    variants = presence.index.tolist()
    weeks_ordered = presence.columns.tolist()

    for row_idx, variant in enumerate(variants):
        for col_idx, week in enumerate(weeks_ordered):
            if presence.loc[variant, week] == 1:
                color = variant_colors.get(variant, "#555555")
                ax.scatter(col_idx, row_idx, color=color, s=100, marker='s')

    # Step 7: Format plot
    ax.set_xticks(range(len(weeks_ordered)))
    ax.set_xticklabels(date_labels, rotation=90, fontsize=10)
    ax.set_xlim(-0.5, len(weeks_ordered) - 0.5)
    ax.set_yticks(range(len(variants)))
    ax.set_yticklabels(variants, fontsize=12)
    ax.set_ylim(-0.5, len(variants) - 0.5)
    ax.set_xlabel("Week")
    ax.set_ylabel("Variant")
    ax.set_title("Weekly Detection of SARS-CoV-2 Variants in Wastewater (Colored by Hex Code), Washington State")
    ax.grid(False)
    plt.tight_layout()
    plt.savefig('results/timeline_updated.jpeg', dpi=300)
    return fig



##############################################################################

# TIMELINE OF DETECTIONS PLOT

def plot_variant_bubble_chart(weighted_df, threshold=0.01):
    """
    Create an interactive bubble plot of SARS-CoV-2 variants by week with uniform circle sizes.
    All bubbles are the same size, only colored by weighted average proportion using viridis palette.

    Parameters:
    - weighted_df: DataFrame with columns ['Week', 'variant', 'weighted_avg', 'total_population']
    - threshold: Minimum weighted_avg proportion to display (default 0.01 = 1%)
    """

    # Filter out zero proportions and anything below threshold
    weighted_df = weighted_df[weighted_df['weighted_avg'] > threshold].copy()

    # Convert weighted_avg to percentage for better display
    weighted_df['percentage'] = weighted_df['weighted_avg'] * 100

    # Create size bins with new specification
    def assign_size_bin(pct):
        if pct < 2:
            return 1
        elif pct <= 10:
            return 2
        elif pct <= 20:
            return 3
        elif pct <= 30:
            return 4
        elif pct <= 40:
            return 5
        elif pct <= 50:
            return 6
        elif pct <= 60:
            return 7
        elif pct <= 70:
            return 8
        elif pct <= 80:
            return 9
        elif pct <= 90:
            return 10
        else:
            return 11

    weighted_df['size_bin'] = weighted_df['percentage'].apply(assign_size_bin)

    # Define size bin labels
    size_labels = {
        1: '1<2%',
        2: '2-10%',
        3: '11-20%',
        4: '21-30%',
        5: '31-40%',
        6: '41-50%',
        7: '51-60%',
        8: '61-70%',
        9: '71-80%',
        10: '81-90%',
        11: '91-100%'
    }
    weighted_df['size_label'] = weighted_df['size_bin'].map(size_labels)

    # Viridis-inspired color palette with white for lowest bin (11 colors)
    viridis_colors = [
        '#ffffff',  # white (1-2% - lowest)
        '#fde724',  # bright yellow
        '#c2df23',
        '#86d549',
        '#52c569',
        '#2ab07f',
        '#1e9b8a',
        '#25858e',
        '#2d6e8e',
        '#38588c',
        '#440154'   # dark purple (91-100% - highest)
    ]

    # Create the bubble chart with uniform size, only color encoding
    chart = alt.Chart(weighted_df).mark_circle(
        size=300,  # Uniform size for all circles
        stroke='#666666', 
        strokeWidth=1
    ).encode(
        x=alt.X('Week:T',  # Changed from 'date:T' to 'Week:T'
                title='Week',
                scale=alt.Scale(padding=20),
                axis=alt.Axis(format='%Y-%m-%d', labelAngle=-90, grid=True)),
        y=alt.Y('variant:N', 
                title='Variant',
                sort=alt.EncodingSortField(field='Week', op='min', order='ascending'),  # Changed from 'date'
                axis=alt.Axis(grid=True)),
        color=alt.Color('size_bin:O',
                        title='Weighted Proportion',
                        scale=alt.Scale(
                            domain=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
                            range=viridis_colors
                        ),
                        legend=alt.Legend(
                            labelExpr="datum.label == 1 ? '1<2%' : datum.label == 2 ? '2-10%' : datum.label == 3 ? '11-20%' : datum.label == 4 ? '21-30%' : datum.label == 5 ? '31-40%' : datum.label == 6 ? '41-50%' : datum.label == 7 ? '51-60%' : datum.label == 8 ? '61-70%' : datum.label == 9 ? '71-80%' : datum.label == 10 ? '81-90%' : '91-100%'",
                            symbolStrokeColor='#666666',
                            symbolStrokeWidth=1
                        )),
        tooltip=[
            alt.Tooltip('variant:N', title='Variant'),
            alt.Tooltip('Week:T', title='Week', format='%Y-%m-%d'),  # Changed from 'date:T'
            alt.Tooltip('percentage:Q', title='Weighted Proportion (%)', format='.2f'),
            alt.Tooltip('total_population:Q', title='Total Population', format=',')
        ]
    ).properties(
        width=1000,
        height=600,
        title={
            "text": "Weekly Detection of SARS-CoV-2 Variants in Wastewater, Washington State",
            "offset": 20
        },
        padding={"top": 40, "bottom": 20, "left": 20, "right": 20}
    ).interactive()

    return chart

# Example usage for marimo
timeline = plot_variant_bubble_chart(
     #weighted_proportions, 
     df_bubble,
#     df_bubble[['variant', 'hex_code']].drop_duplicates(),
     threshold=0.01  # 1% threshold
)
timeline.save('results/bubble_plot.html')
timeline.save('results/bubble_plot.png', dpi=600, scale_factor=4, engine='vl-convert')




##############################################################################

# PLOT LINE GRAPH
def get_top_variants(weighted_df, top_n=3):
    top_variants = (
        weighted_df.groupby('variant')['weighted_avg']
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
        .index
        .tolist()
    )

    return top_variants


def create_line_graph(weighted_df, top_variants):   
    # Filter to top variants and recent weeks only
    filtered = weighted_df[
        (weighted_df['variant'].isin(top_variants)) 
    ]

    pivoted = filtered.pivot(index='Week', columns='variant', values='weighted_avg').fillna(0)
    pivoted.index = pd.to_datetime(pivoted.index).strftime('%Y-%m-%d')

    variant_colors = weighted_df[['variant', 'hex_code']].drop_duplicates().set_index('variant')['hex_code'].to_dict()

    fig, ax = plt.subplots(figsize=(12, 8))
    for variant in top_variants:
        ax.plot(pivoted.index, pivoted[variant], label=variant, color=variant_colors.get(variant, 'black'))
        ax.text(
            pivoted.index[-1],
            pivoted[variant].iloc[-1],
            variant,
            fontsize=11,
            ha='left',
            va='center'
        )

    ax.set_title('Top Recent SARS-CoV-2 Variants in Wastewater, Washington State')
    ax.set_ylabel('Proportion')
    ax.set_xlabel('Week')
    ax.tick_params(axis='x', rotation=45)
    ax.legend(title='Variant', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.savefig('results/line_graph.jpeg', dpi=300)
    return fig

##############################################################################

# PLOT HEATMAP

def create_filtered_heatmap(weighted_df, min_percent=10):
    """
    Create a heatmap of SARS-CoV-2 variants showing proportions over recent weeks.

    Parameters:
    - weighted_df: DataFrame with columns ['Week', 'variant', 'weighted_avg', 'total_population']
    - min_percent: Minimum percentage threshold to include a variant (default 10%)
    """

   # Pivot table
    pivot = weighted_df.pivot(index='variant', columns='Week', values='weighted_avg').fillna(0) * 100
    # Filter variants by min_percent threshold
    filtered = pivot[pivot.max(axis=1) >= min_percent]

    # format date for plotting
    def week_to_date(week):
        """Convert week to string format for plotting"""
        return pd.to_datetime(week).strftime('%Y-%m-%d')

    filtered.columns = [week_to_date(week) for week in filtered.columns]

    # Reorder columns
    filtered = filtered[sorted(filtered.columns)]

    # Create custom colormap matching bubble plot
    # Colors from bubble plot: white, yellow, green-cyan gradient, blue, purple
    colors_list = [
        '#ffffff',  # white (0-2%)
        '#fde724',  # bright yellow (2-10%)
        '#c2df23',  # yellow-green (10-20%)
        '#86d549',  # green (20-30%)
        '#52c569',  # green (30-40%)
        '#2ab07f',  # green-cyan (40-50%)
        '#1e9b8a',  # cyan (50-60%)
        '#25858e',  # cyan-blue (60-70%)
        '#2d6e8e',  # blue (70-80%)
        '#38588c',  # blue-purple (80-90%)
        '#440154'   # dark purple (90-100%)
    ]

    # Create boundaries for the bins
    boundaries = [0, 2, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

    # Create custom colormap
    cmap = mcolors.ListedColormap(colors_list)
    norm = mcolors.BoundaryNorm(boundaries, cmap.N)

    # Plot
    plt.figure(figsize=(12, 8))
    sns.heatmap(
        filtered,
        annot=True,
        fmt=".2g",
        cmap=cmap,
        norm=norm,
        cbar_kws={'label': 'Proportion (%)', 'boundaries': boundaries, 'ticks': boundaries},
        linewidths=0.5,
        linecolor='lightgray'
    )
    plt.title('Variants ≥10% in Any Week (Past 12 Weeks), Washington State')
    plt.xlabel('Sample Collection Week')
    plt.ylabel('Variant')
    plt.savefig('results/heatmap.jpeg', dpi=300, bbox_inches='tight')
    plt.tight_layout()
    return plt.gcf()

##############################################################################

# PLOT WEEKLY DOMINANT VARIANTS

def plot_dominant_variant_maps(config, weighted_df):
    """
    Generates weekly maps of the dominant SARS-CoV-2 variant in each WA county.
    Shows the actual county-specific percentage of the dominant variant.
    Counties not enrolled in surveillance are shown in grey.

    Parameters:
    -----------
    config : dict
        Full config dictionary loaded from config.yaml
    weighted_df : DataFrame
        Output from calculate_county_weighted_variant_prevalence()
        Contains: Week, county, variant, weighted_avg, hex_code

    Config structure:
        geographic_data:
            shapefiles_dir: 'defaults/'
            non_sampled_counties: 'defaults/non_sampled_counties.csv'
    """

    # Step 1. Check if x exists in config

    # Check if geographic_data exists in config
    if 'geographic_data' not in config:
        raise ValueError("'geographic_data' not found in Config")

    geographic_data = config['geographic_data']

    # Check if shapefiles_dir exists in geographic_data
    if 'shapefiles_dir' not in geographic_data:
        raise ValueError("'shapefiles_dir' not found in geographic_data Config")

    # Check if non_sampled_counties exists in geographic_data
    if 'non_sampled_counties' not in geographic_data:
        raise ValueError("'non_sampled_counties' not found in geographic_data Config")

    # Step 2  Set up shapefile and non_sampled_counties
    # Build shapefile path
    shapefile_path = os.path.join(geographic_data['shapefiles_dir'], 'WA_County_Boundaries.shp')

    # Read non-sampled counties from CSV
    try:
        non_sampled_df = pd.read_csv(geographic_data['non_sampled_counties'])
        NON_SAMPLED_COUNTIES = non_sampled_df['non_sampled_county'].tolist()
    except FileNotFoundError:
        raise FileNotFoundError(f"Non-sampled counties file not found at: {geographic_data['non_sampled_counties']}")

    # Step 3: Load and normalize shapefile
    try:
        wa_shape = gpd.read_file(shapefile_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Shapefile not found at: {shapefile_path}")

    wa_shape = wa_shape.rename(columns={"JURISDIC_3": "county"})
    wa_shape['county'] = wa_shape['county'].str.title()

    # Step 4: Format dates - keep datetime for sorting/display, create formatted version
    weighted_df = weighted_df.copy()
    weighted_df['Week_dt'] = pd.to_datetime(weighted_df['Week'])
    weighted_df['Week_formatted'] = weighted_df['Week_dt'].dt.strftime('%Y-%m-%d')

    # Step 5: Plotting
    # 5.a Get unique weeks to plot
    weeks_to_plot = weighted_df['Week_formatted'].unique()

    if len(weeks_to_plot) == 0:
        print("No usable weekly data available.")
        return

    # 5.b Set up plots
    n = len(weeks_to_plot)
    rows = (n + 3) // 4
    cols = 4

    from matplotlib.gridspec import GridSpec
    import matplotlib.patheffects as patheffects

    fig = plt.figure(figsize=(cols * 6, rows * 6 + 2))
    gs = GridSpec(rows + 1, cols, height_ratios=[1]*rows + [0.2])
    axes = [fig.add_subplot(gs[i, j]) for i in range(rows) for j in range(cols)]

    plotted_variants = []

    # 5.c iterate through weeks and plot maps
    for i, week in enumerate(weeks_to_plot):
        ax = axes[i]
        print(f"Processing week: {week}")

        week_data = weighted_df[weighted_df['Week_formatted'] == week]
        if week_data.empty:
            print(f"  [SKIPPED] No data found for week {week}")
            continue

        # Find dominant variant per county
        dominant = week_data.loc[week_data.groupby('county')['weighted_avg'].idxmax()]

        # Merge with shapefile
        map_df = wa_shape.merge(
            dominant[['county', 'variant', 'hex_code', 'weighted_avg']], 
            on='county', 
            how='left'
        )

        # Apply colors: grey=not enrolled, white=no data, color=variant
        map_df['hex_code'] = map_df.apply(
            lambda row: '#D3D3D3' if row['county'] in NON_SAMPLED_COUNTIES 
            else (row['hex_code'] if pd.notna(row['hex_code']) else '#FFFFFF'),
            axis=1
        )

        map_df['hex_code'] = map_df['hex_code'].astype(str)

        # Collect variants for legend
        variant_data = map_df[
            (map_df['variant'].notna()) & 
            (~map_df['county'].isin(NON_SAMPLED_COUNTIES))
        ][['variant', 'hex_code']].drop_duplicates()

        if not variant_data.empty:
            plotted_variants.append(variant_data)

        # Validate hex codes
        bad_rows = map_df[~map_df['hex_code'].str.match(r'^#(?:[0-9a-fA-F]{3}){1,2}$')]
        if not bad_rows.empty:
            print("❌ Found invalid hex codes:")
            print(bad_rows[['county', 'variant', 'hex_code']])
            raise ValueError("Stopping: invalid hex codes present.")

        # Plot map
        map_df.plot(ax=ax, color=map_df['hex_code'], edgecolor='black')

        # Add percentage annotations with black outline
        counties_with_data = map_df[
            (map_df['variant'].notna()) & 
            (~map_df['county'].isin(NON_SAMPLED_COUNTIES))
        ]

        for idx, row in counties_with_data.iterrows():
            centroid = row.geometry.centroid
            percentage = row['weighted_avg'] * 100

            ax.annotate(
                f"{percentage:.0f}%",
                xy=(centroid.x, centroid.y),
                ha='center',
                va='center',
                fontsize=14,
                fontweight='bold',
                color='white',
                path_effects=[
                    patheffects.Stroke(linewidth=3, foreground='black'),
                    patheffects.Normal()
                ]
            )

        # Get the datetime for title
        title_date = week_data['Week_dt'].iloc[0]
        ax.set_title(f"Dominant Variant by County, Week of {title_date.strftime('%b %d, %Y')}", fontsize=16)
        ax.axis('off')

    # Step 6 Legend
    #Compile legend variants
    if plotted_variants:
        legend_variants = pd.concat(plotted_variants).drop_duplicates().sort_values(by='variant')
    else:
        legend_variants = pd.DataFrame(columns=['variant', 'hex_code'])

    # Remove unused axes
    for ax in axes[len(weeks_to_plot):]:
        fig.delaxes(ax)

    # Create legend
    legend_elements = [
        Line2D([0], [0], marker='o', color='w', label=variant, markersize=10, 
               markerfacecolor=hex_code, markeredgecolor='black', markeredgewidth=1.5)
        for variant, hex_code in zip(legend_variants['variant'], legend_variants['hex_code'])
        if isinstance(hex_code, str) and hex_code.startswith('#')
    ]

    legend_elements.append(
        Line2D([0], [0], marker='o', color='w', label='Not Enrolled', 
               markersize=10, markerfacecolor='#D3D3D3', markeredgecolor='black', markeredgewidth=1.5)
    )
    legend_elements.append(
        Line2D([0], [0], marker='o', color='w', label='No Data', 
               markersize=10, markerfacecolor='#FFFFFF', markeredgecolor='black', markeredgewidth=1.5)
    )

    legend_ax = fig.add_subplot(gs[-1, :])
    legend_ax.axis('off')

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

    # Step 7 plotting
    plt.tight_layout()
    plt.savefig('results/dominant_variants_map_weighted.jpeg', dpi=300, bbox_inches='tight')
    return fig

# CALL PLOT FUNCTION

##############################################################################

# MAIN WRAPPER

