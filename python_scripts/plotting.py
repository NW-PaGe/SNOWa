"""
Create SARS-CoV-2 wastewater surveillance plots from pre-filtered plotting CSVs.

This script is designed to run from Snakemake, but it can also be run directly
from the command line for debugging.

Expected Snakemake contract
---------------------------
input:
    filtered = list of filtered CSVs, one per plot key
output:
    plots = list of final plot files, one per plot key
    plot_list = results/plots/plot_list.txt
params:
    plot_keys = list of plot keys, e.g. ["stacked_bar_plt", "qc_pa_plt", ...]
    plot_extensions = dict mapping plot key -> file extension
    config = full config dictionary

Plot key naming pattern
-----------------------
stacked_bar_plt  -> results/filtered/stacked_bar_plt_filtered.csv  -> results/plots/stacked_bar_plt.jpeg
bubble_plt       -> results/filtered/bubble_plt_filtered.csv       -> results/plots/bubble_plt.jpeg
"""

import argparse
import os
import re
from typing import Dict, Iterable, List, Mapping

import geopandas as gpd
import matplotlib

# Use a non-interactive backend for Snakemake/container execution.
matplotlib.use("Agg")

import matplotlib.colors as mcolors
import matplotlib.gridspec as gridspec
import matplotlib.patheffects as patheffects
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import yaml
from matplotlib.lines import Line2D


##############################################################################
# DEFAULTS

DEFAULT_PLOT_EXTENSIONS = {
    "stacked_bar_plt": "jpeg",
    "qc_pa_plt": "jpeg",
    "bubble_plt": "jpeg",
    "line_plt": "jpeg",
    "heatmap_plt": "jpeg",
    "weekly_maps_plt": "jpeg",
}

DEFAULT_PLOT_PARAMS = {
    "stacked_bar_plt": {"table_threshold": 0.001},
    "qc_pa_plt": {},
    "bubble_plt": {"threshold": 0.01},
    "line_plt": {"top_n": 3},
    "heatmap_plt": {"min_percent": 10},
    "weekly_maps_plt": {},
}

REQUIRED_COLUMNS = {
    "stacked_bar_plt": ["Week", "variant", "weighted_avg", "hex_code"],
    "qc_pa_plt": ["Week", "variant", "weighted_avg", "hex_code"],
    "bubble_plt": ["Week", "variant", "weighted_avg"],
    "line_plt": ["Week", "variant", "weighted_avg", "hex_code"],
    "heatmap_plt": ["Week", "variant", "weighted_avg"],
    "weekly_maps_plt": ["Week", "county", "variant", "weighted_avg", "hex_code"],
}


##############################################################################
# SHARED HELPERS


def week_to_date(week) -> str:
    """Convert a Week value to YYYY-MM-DD string format for display."""
    return pd.to_datetime(week).strftime("%Y-%m-%d")


def normalize_week_column(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Week to datetime if the column exists."""
    df = df.copy()
    if "Week" in df.columns:
        df["Week"] = pd.to_datetime(df["Week"])
    return df


def make_variant_color_map(df: pd.DataFrame) -> Dict[str, str]:
    """Build variant -> hex color mapping from a dataframe."""
    if "variant" not in df.columns or "hex_code" not in df.columns:
        return {}

    color_map = (
        df[["variant", "hex_code"]]
        .dropna(subset=["variant"])
        .drop_duplicates()
        .set_index("variant")["hex_code"]
        .to_dict()
    )

    # Replace missing or invalid colors with a neutral fallback.
    return {
        variant: color if is_valid_hex_color(color) else "#999999"
        for variant, color in color_map.items()
    }


def is_valid_hex_color(value) -> bool:
    """Return True if value is a valid 3- or 6-digit hex color."""
    return isinstance(value, str) and re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", value) is not None


def validate_required_columns(df: pd.DataFrame, plot_key: str) -> None:
    """Raise a helpful error if a plot dataframe is missing required columns."""
    required = REQUIRED_COLUMNS.get(plot_key, [])
    missing = [column for column in required if column not in df.columns]

    if missing:
        raise ValueError(
            f"Filtered dataframe for '{plot_key}' is missing required columns: {missing}. "
            f"Available columns: {list(df.columns)}"
        )


def make_empty_figure(title: str, message: str):
    """Create a placeholder figure when a filtered dataframe has no plottable rows."""
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axis("off")
    ax.set_title(title)
    ax.text(0.5, 0.5, message, ha="center", va="center", fontsize=14)
    plt.tight_layout()
    return fig


def get_plot_params(config: Mapping, plot_key: str) -> Dict:
    """
    Get optional plot-specific parameters from config.

    This is intentionally permissive. If your config does not yet have a
    plots.params block, defaults are used.

    Optional future config structure:
        plots:
          params:
            bubble_plt:
              threshold: 0.01
            heatmap_plt:
              min_percent: 10
    """
    params = dict(DEFAULT_PLOT_PARAMS.get(plot_key, {}))
    config_params = config.get("plots", {}).get("params", {}).get(plot_key, {})

    if config_params:
        params.update(config_params)

    return params


##############################################################################
# STACKED BAR PLOT


def pivot_to_table(df_stacked_bar: pd.DataFrame) -> pd.DataFrame:
    """
    Pivot weighted proportions into wide format.

    Rows = Week
    Columns = variants
    Values = weighted_avg
    """
    pivot_table = df_stacked_bar.pivot_table(
        index="Week",
        columns="variant",
        values="weighted_avg",
        fill_value=0,
        aggfunc="sum",
    )
    return pivot_table.sort_index()


def plot_stacked_bar(df_stacked_bar: pd.DataFrame, table_threshold: float = 0.001):
    """
    Plot a stacked bar chart of variant proportions by week.

    Includes a side table showing the most recent week's proportions above the
    supplied threshold.
    """
    if df_stacked_bar.empty:
        return make_empty_figure(
            "Weekly Population-Weighted SARS-CoV-2 Variant Proportions",
            "No rows available after filtering.",
        )

    pivot_table = pivot_to_table(df_stacked_bar)

    if pivot_table.empty:
        return make_empty_figure(
            "Weekly Population-Weighted SARS-CoV-2 Variant Proportions",
            "No plottable variant proportions available.",
        )

    variant_colors = make_variant_color_map(df_stacked_bar)
    colors = [variant_colors.get(variant, "#999999") for variant in pivot_table.columns]
    date_labels = [week_to_date(week) for week in pivot_table.index]

    most_recent_week = pivot_table.index[-1]
    recent_data = pivot_table.iloc[-1]
    recent_data_filtered = recent_data[recent_data >= table_threshold].sort_values(ascending=False)

    fig = plt.figure(figsize=(32, 14))
    gs = gridspec.GridSpec(1, 2, width_ratios=[4, 1], wspace=0.25)

    ax_main = fig.add_subplot(gs[0])
    pivot_table.plot(
        kind="bar",
        stacked=True,
        ax=ax_main,
        width=1.00,
        color=colors,
        edgecolor="white",
        linewidth=0.5,
    )

    ax_main.set_xlabel("Week of Sample Collection Date", fontsize=12)
    ax_main.set_ylabel("Variant Population-Weighted Proportion", fontsize=12)
    ax_main.set_title(
        "Weekly Population-Weighted SARS-CoV-2 Variant Proportions Across All Sampling Sites, Washington State",
        fontsize=13,
        pad=20,
    )
    ax_main.set_xticks(range(len(pivot_table.index)))
    ax_main.set_xticklabels(date_labels, rotation=90, fontsize=12)
    ax_main.legend(
        title="Variant",
        bbox_to_anchor=(0.5, -0.15),
        loc="upper center",
        ncol=min(12, len(pivot_table.columns)),
        fontsize=12,
    )

    ax_table = fig.add_subplot(gs[1])
    ax_table.axis("off")
    ax_table.text(
        0.5,
        0.98,
        f"Most Recent Week\n{week_to_date(most_recent_week)}",
        ha="center",
        va="top",
        fontsize=12,
        weight="bold",
        transform=ax_table.transAxes,
    )

    table_data = [
        [variant, f"{proportion * 100:.1f}%"]
        for variant, proportion in recent_data_filtered.items()
    ]

    if table_data:
        table = ax_table.table(
            cellText=table_data,
            colLabels=["Variant", "Proportion"],
            cellLoc="left",
            loc="upper center",
            bbox=[0, 0.05, 1, 0.85],
        )

        table.auto_set_font_size(False)
        table.set_fontsize(14)
        table.scale(1, 2.2)

        for i, (variant, _) in enumerate(table_data):
            cell = table[(i + 1, 0)]
            cell.set_facecolor(variant_colors.get(variant, "#999999"))
            cell.set_text_props(weight="bold", color="white")

        for i in range(2):
            table[(0, i)].set_facecolor("#4472C4")
            table[(0, i)].set_text_props(weight="bold", color="white")

    plt.tight_layout()
    return fig


##############################################################################
# PRESENCE / ABSENCE QA PLOT


def plot_variant_presence_by_week(df: pd.DataFrame):
    """
    Plot weekly SARS-CoV-2 variant detection timeline using presence/absence.

    Input dataframe columns:
        Week, variant, hex_code, weighted_avg
    """
    if df.empty:
        return make_empty_figure(
            "Weekly Detection of SARS-CoV-2 Variants in Wastewater",
            "No rows available after filtering.",
        )

    df_detected = df[df["weighted_avg"] > 0].copy()
    week_labels = sorted(df["Week"].unique())

    if df_detected.empty or not week_labels:
        return make_empty_figure(
            "Weekly Detection of SARS-CoV-2 Variants in Wastewater",
            "No detected variants available after filtering.",
        )

    variant_colors = make_variant_color_map(df)

    presence = (
        df_detected.groupby(["variant", "Week"])
        .size()
        .unstack(fill_value=0)
        .reindex(columns=week_labels, fill_value=0)
    )
    presence = (presence > 0).astype(int)

    first_appearance = presence.idxmax(axis=1)
    presence = presence.loc[first_appearance.sort_values(ascending=False).index]

    date_labels = [week_to_date(week) for week in week_labels]

    fig, ax = plt.subplots(figsize=(16, 18))
    variants = presence.index.tolist()
    weeks_ordered = presence.columns.tolist()

    for row_idx, variant in enumerate(variants):
        for col_idx, week in enumerate(weeks_ordered):
            if presence.loc[variant, week] == 1:
                color = variant_colors.get(variant, "#555555")
                ax.scatter(col_idx, row_idx, color=color, s=100, marker="s")

    ax.set_xticks(range(len(weeks_ordered)))
    ax.set_xticklabels(date_labels, rotation=90, fontsize=10)
    ax.set_xlim(-0.5, len(weeks_ordered) - 0.5)
    ax.set_yticks(range(len(variants)))
    ax.set_yticklabels(variants, fontsize=12)
    ax.set_ylim(-0.5, len(variants) - 0.5)
    ax.set_xlabel("Week")
    ax.set_ylabel("Variant")
    ax.set_title(
        "Weekly Detection of SARS-CoV-2 Variants in Wastewater (Colored by Hex Code), Washington State"
    )
    ax.grid(False)
    plt.tight_layout()
    return fig


##############################################################################
# BUBBLE PLOT


def plot_variant_bubble_chart(weighted_df: pd.DataFrame, threshold: float = 0.01):
    """
    Create a static matplotlib bubble chart of SARS-CoV-2 variants by week.

    This returns a matplotlib Figure and is saved as JPEG like the other
    static matplotlib plots.
    """
    weighted_df = weighted_df[weighted_df["weighted_avg"] > threshold].copy()

    if weighted_df.empty:
        return make_empty_figure(
            "Weekly Detection of SARS-CoV-2 Variants in Wastewater, Washington State",
            f"No variants above {threshold * 100:g}% after filtering.",
        )

    weighted_df["percentage"] = weighted_df["weighted_avg"] * 100

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

    weighted_df["size_bin"] = weighted_df["percentage"].apply(assign_size_bin)

    size_labels = {
        1: "1<2%",
        2: "2-10%",
        3: "11-20%",
        4: "21-30%",
        5: "31-40%",
        6: "41-50%",
        7: "51-60%",
        8: "61-70%",
        9: "71-80%",
        10: "81-90%",
        11: "91-100%",
    }

    viridis_colors = [
        "#ffffff",
        "#fde724",
        "#c2df23",
        "#86d549",
        "#52c569",
        "#2ab07f",
        "#1e9b8a",
        "#25858e",
        "#2d6e8e",
        "#38588c",
        "#440154",
    ]

    weeks = sorted(weighted_df["Week"].unique())
    variants = (
        weighted_df.groupby("variant")["Week"]
        .min()
        .sort_values(ascending=False)
        .index
        .tolist()
    )

    x_positions = {week: idx for idx, week in enumerate(weeks)}
    y_positions = {variant: idx for idx, variant in enumerate(variants)}

    weighted_df["x_pos"] = weighted_df["Week"].map(x_positions)
    weighted_df["y_pos"] = weighted_df["variant"].map(y_positions)
    weighted_df["color"] = weighted_df["size_bin"].apply(lambda b: viridis_colors[int(b) - 1])

    fig_width = max(12, len(weeks) * 0.45)
    fig_height = max(8, len(variants) * 0.28)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    ax.scatter(
        weighted_df["x_pos"],
        weighted_df["y_pos"],
        s=300,
        c=weighted_df["color"],
        edgecolors="#666666",
        linewidths=1,
    )

    ax.set_xticks(range(len(weeks)))
    ax.set_xticklabels([week_to_date(week) for week in weeks], rotation=90, fontsize=10)
    ax.set_yticks(range(len(variants)))
    ax.set_yticklabels(variants, fontsize=10)
    ax.set_xlabel("Week")
    ax.set_ylabel("Variant")
    ax.set_title(
        "Weekly Detection of SARS-CoV-2 Variants in Wastewater, Washington State"
    )
    ax.set_xlim(-0.5, len(weeks) - 0.5)
    ax.set_ylim(-0.5, len(variants) - 0.5)
    ax.grid(True, axis="both", linewidth=0.5, alpha=0.3)

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=size_labels[bin_id],
            markerfacecolor=viridis_colors[bin_id - 1],
            markeredgecolor="#666666",
            markersize=10,
        )
        for bin_id in range(1, 12)
    ]
    ax.legend(
        handles=legend_elements,
        title="Weighted Proportion",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0,
    )

    plt.tight_layout()
    return fig


##############################################################################
# LINE GRAPH


def get_top_variants(weighted_df: pd.DataFrame, top_n: int = 3) -> List[str]:
    """Return top variants by mean weighted average."""
    if weighted_df.empty:
        return []

    return (
        weighted_df.groupby("variant")["weighted_avg"]
        .mean()
        .sort_values(ascending=False)
        .head(top_n)
        .index
        .tolist()
    )


def create_line_graph(weighted_df: pd.DataFrame, top_n: int = 3):
    """Plot top variants over time."""
    top_variants = get_top_variants(weighted_df, top_n=top_n)

    if not top_variants:
        return make_empty_figure(
            "Top Recent SARS-CoV-2 Variants in Wastewater, Washington State",
            "No rows available after filtering.",
        )

    filtered = weighted_df[weighted_df["variant"].isin(top_variants)].copy()
    pivoted = filtered.pivot_table(
        index="Week",
        columns="variant",
        values="weighted_avg",
        fill_value=0,
        aggfunc="sum",
    ).sort_index()

    if pivoted.empty:
        return make_empty_figure(
            "Top Recent SARS-CoV-2 Variants in Wastewater, Washington State",
            "No plottable variant proportions available.",
        )

    pivoted.index = pd.to_datetime(pivoted.index).strftime("%Y-%m-%d")
    variant_colors = make_variant_color_map(weighted_df)

    fig, ax = plt.subplots(figsize=(12, 8))

    for variant in top_variants:
        if variant not in pivoted.columns:
            continue

        ax.plot(
            pivoted.index,
            pivoted[variant],
            label=variant,
            color=variant_colors.get(variant, "black"),
        )
        ax.text(
            pivoted.index[-1],
            pivoted[variant].iloc[-1],
            variant,
            fontsize=11,
            ha="left",
            va="center",
        )

    ax.set_title("Top Recent SARS-CoV-2 Variants in Wastewater, Washington State")
    ax.set_ylabel("Proportion")
    ax.set_xlabel("Week")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(title="Variant", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    return fig


##############################################################################
# HEATMAP


def create_filtered_heatmap(weighted_df: pd.DataFrame, min_percent: float = 10):
    """
    Create a heatmap of variants over recent weeks.

    min_percent is expressed as a percentage, not a proportion.
    """
    if weighted_df.empty:
        return make_empty_figure(
            "Variants in Wastewater, Washington State",
            "No rows available after filtering.",
        )

    pivot = (
        weighted_df.pivot_table(
            index="variant",
            columns="Week",
            values="weighted_avg",
            fill_value=0,
            aggfunc="sum",
        )
        * 100
    )

    filtered = pivot[pivot.max(axis=1) >= min_percent]

    if filtered.empty:
        return make_empty_figure(
            f"Variants >= {min_percent:g}% in Any Week, Washington State",
            f"No variants reached {min_percent:g}% after filtering.",
        )

    filtered.columns = [week_to_date(week) for week in filtered.columns]
    filtered = filtered[sorted(filtered.columns)]

    colors_list = [
        "#ffffff",
        "#fde724",
        "#c2df23",
        "#86d549",
        "#52c569",
        "#2ab07f",
        "#1e9b8a",
        "#25858e",
        "#2d6e8e",
        "#38588c",
        "#440154",
    ]
    boundaries = [0, 2, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    cmap = mcolors.ListedColormap(colors_list)
    norm = mcolors.BoundaryNorm(boundaries, cmap.N)

    fig, ax = plt.subplots(figsize=(12, 8))
    sns.heatmap(
        filtered,
        annot=True,
        fmt=".2g",
        cmap=cmap,
        norm=norm,
        cbar_kws={"label": "Proportion (%)", "boundaries": boundaries, "ticks": boundaries},
        linewidths=0.5,
        linecolor="lightgray",
        ax=ax,
    )
    ax.set_title(f"Variants >= {min_percent:g}% in Any Week, Washington State")
    ax.set_xlabel("Sample Collection Week")
    ax.set_ylabel("Variant")
    plt.tight_layout()
    return fig


##############################################################################
# WEEKLY DOMINANT VARIANT MAPS


def plot_dominant_variant_maps(config: Mapping, weighted_df: pd.DataFrame):
    """
    Generate weekly maps of the dominant SARS-CoV-2 variant in each WA county.

    Requires config['geographic_data']['shapefiles_dir'] and
    config['geographic_data']['non_sampled_counties'].
    """
    if weighted_df.empty:
        return make_empty_figure(
            "Dominant Variant by County, Washington State",
            "No rows available after filtering.",
        )

    if "geographic_data" not in config:
        raise ValueError(
            "'geographic_data' not found in config. Add geographic_data.shapefiles_dir "
            "and geographic_data.non_sampled_counties before running weekly_maps_plt."
        )

    geographic_data = config["geographic_data"]

    if "shapefiles_dir" not in geographic_data:
        raise ValueError("'shapefiles_dir' not found in config['geographic_data']")

    if "non_sampled_counties" not in geographic_data:
        raise ValueError("'non_sampled_counties' not found in config['geographic_data']")

    shapefile_path = os.path.join(geographic_data["shapefiles_dir"], "WA_County_Boundaries.shp")

    try:
        non_sampled_df = pd.read_csv(geographic_data["non_sampled_counties"])
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Non-sampled counties file not found at: {geographic_data['non_sampled_counties']}"
        ) from exc

    if "non_sampled_county" not in non_sampled_df.columns:
        raise ValueError(
            f"Expected column 'non_sampled_county' in {geographic_data['non_sampled_counties']}"
        )

    non_sampled_counties = non_sampled_df["non_sampled_county"].str.title().tolist()

    try:
        wa_shape = gpd.read_file(shapefile_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Shapefile not found at: {shapefile_path}") from exc

    if "JURISDIC_3" not in wa_shape.columns and "county" not in wa_shape.columns:
        raise ValueError(
            "County shapefile must contain either 'JURISDIC_3' or 'county' column."
        )

    if "JURISDIC_3" in wa_shape.columns:
        wa_shape = wa_shape.rename(columns={"JURISDIC_3": "county"})

    wa_shape["county"] = wa_shape["county"].str.title()

    weighted_df = weighted_df.copy()
    weighted_df["county"] = weighted_df["county"].str.title()
    weighted_df["Week_dt"] = pd.to_datetime(weighted_df["Week"])
    weighted_df["Week_formatted"] = weighted_df["Week_dt"].dt.strftime("%Y-%m-%d")

    weeks_to_plot = sorted(weighted_df["Week_formatted"].unique())

    if len(weeks_to_plot) == 0:
        return make_empty_figure(
            "Dominant Variant by County, Washington State",
            "No usable weekly data available.",
        )

    n = len(weeks_to_plot)
    cols = 4
    rows = (n + cols - 1) // cols

    fig = plt.figure(figsize=(cols * 6, rows * 6 + 2))
    gs = gridspec.GridSpec(rows + 1, cols, height_ratios=[1] * rows + [0.2])
    axes = [fig.add_subplot(gs[i, j]) for i in range(rows) for j in range(cols)]

    plotted_variants = []

    for i, week in enumerate(weeks_to_plot):
        ax = axes[i]
        print(f"Processing week: {week}")

        week_data = weighted_df[weighted_df["Week_formatted"] == week]
        if week_data.empty:
            ax.axis("off")
            ax.set_title(f"No data for week of {week}")
            continue

        dominant = week_data.loc[week_data.groupby("county")["weighted_avg"].idxmax()]

        map_df = wa_shape.merge(
            dominant[["county", "variant", "hex_code", "weighted_avg"]],
            on="county",
            how="left",
        )

        map_df["hex_code"] = map_df.apply(
            lambda row: "#D3D3D3"
            if row["county"] in non_sampled_counties
            else (row["hex_code"] if pd.notna(row["hex_code"]) else "#FFFFFF"),
            axis=1,
        )
        map_df["hex_code"] = map_df["hex_code"].astype(str)

        bad_rows = map_df[~map_df["hex_code"].apply(is_valid_hex_color)]
        if not bad_rows.empty:
            print("Found invalid hex codes:")
            print(bad_rows[["county", "variant", "hex_code"]])
            raise ValueError("Stopping: invalid hex codes present.")

        variant_data = map_df[
            (map_df["variant"].notna())
            & (~map_df["county"].isin(non_sampled_counties))
        ][["variant", "hex_code"]].drop_duplicates()

        if not variant_data.empty:
            plotted_variants.append(variant_data)

        map_df.plot(ax=ax, color=map_df["hex_code"], edgecolor="black")

        counties_with_data = map_df[
            (map_df["variant"].notna())
            & (~map_df["county"].isin(non_sampled_counties))
        ]

        for _, row in counties_with_data.iterrows():
            centroid = row.geometry.centroid
            percentage = row["weighted_avg"] * 100

            ax.annotate(
                f"{percentage:.0f}%",
                xy=(centroid.x, centroid.y),
                ha="center",
                va="center",
                fontsize=14,
                fontweight="bold",
                color="white",
                path_effects=[
                    patheffects.Stroke(linewidth=3, foreground="black"),
                    patheffects.Normal(),
                ],
            )

        title_date = week_data["Week_dt"].iloc[0]
        ax.set_title(
            f"Dominant Variant by County, Week of {title_date.strftime('%b %d, %Y')}",
            fontsize=16,
        )
        ax.axis("off")

    for ax in axes[len(weeks_to_plot) :]:
        fig.delaxes(ax)

    if plotted_variants:
        legend_variants = pd.concat(plotted_variants).drop_duplicates().sort_values(by="variant")
    else:
        legend_variants = pd.DataFrame(columns=["variant", "hex_code"])

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label=variant,
            markersize=10,
            markerfacecolor=hex_code,
            markeredgecolor="black",
            markeredgewidth=1.5,
        )
        for variant, hex_code in zip(legend_variants["variant"], legend_variants["hex_code"])
        if is_valid_hex_color(hex_code)
    ]

    legend_elements.append(
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="Not Enrolled",
            markersize=10,
            markerfacecolor="#D3D3D3",
            markeredgecolor="black",
            markeredgewidth=1.5,
        )
    )
    legend_elements.append(
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            label="No Data",
            markersize=10,
            markerfacecolor="#FFFFFF",
            markeredgecolor="black",
            markeredgewidth=1.5,
        )
    )

    legend_ax = fig.add_subplot(gs[-1, :])
    legend_ax.axis("off")
    legend_ax.legend(
        handles=legend_elements,
        title="Variants",
        title_fontsize=18,
        loc="center",
        ncol=6,
        fontsize=14,
        markerscale=2,
        frameon=False,
    )

    plt.tight_layout()
    return fig


##############################################################################
# SAVE HELPERS


def save_matplotlib_figure(fig, output_path: str, dpi: int = 300) -> None:
    """Save a matplotlib figure and close it."""
    if fig is None:
        raise ValueError(f"No matplotlib figure was created for {output_path}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


def write_plot_list(output_paths: Mapping[str, str], plot_list_path: str) -> None:
    """Write a simple tab-delimited list of generated plots."""
    os.makedirs(os.path.dirname(plot_list_path), exist_ok=True)

    with open(plot_list_path, "w") as f:
        for plot_key, output_path in output_paths.items():
            f.write(f"{plot_key}\t{output_path}\n")


##############################################################################
# PLOT DISPATCHER


def run_plot(plot_key: str, df: pd.DataFrame, config: Mapping):
    """Call the correct plotting function for one plot key."""
    params = get_plot_params(config, plot_key)

    if plot_key == "stacked_bar_plt":
        return plot_stacked_bar(df, **params), "matplotlib"
    elif plot_key == "qc_pa_plt":
        return plot_variant_presence_by_week(df), "matplotlib"
    elif plot_key == "bubble_plt":
        return plot_variant_bubble_chart(df, **params), "matplotlib"
    elif plot_key == "line_plt":
        return create_line_graph(df, **params), "matplotlib"
    elif plot_key == "heatmap_plt":
        return create_filtered_heatmap(df, **params), "matplotlib"
    elif plot_key == "weekly_maps_plt":
        return plot_dominant_variant_maps(config, df), "matplotlib"

    raise ValueError(f"No plotting function registered for plot key: {plot_key}")


def run_all_plots(
    input_paths: Mapping[str, str],
    output_paths: Mapping[str, str],
    plot_keys: Iterable[str],
    config: Mapping,
) -> None:
    """Read filtered CSVs, create plots, and save outputs."""
    for plot_key in plot_keys:
        if plot_key not in input_paths:
            raise ValueError(f"No input path found for plot key: {plot_key}")
        if plot_key not in output_paths:
            raise ValueError(f"No output path found for plot key: {plot_key}")

        input_path = input_paths[plot_key]
        output_path = output_paths[plot_key]

        print(f"Creating {plot_key}", flush=True)
        print(f"  input:  {input_path}", flush=True)
        print(f"  output: {output_path}", flush=True)

        try:
            df = pd.read_csv(input_path)
            df = normalize_week_column(df)
            validate_required_columns(df, plot_key)

            plot_obj, plot_kind = run_plot(plot_key, df, config)

            if plot_kind != "matplotlib":
                raise ValueError(f"Unknown plot kind for {plot_key}: {plot_kind}")

            save_matplotlib_figure(plot_obj, output_path)

        except Exception as exc:
            raise RuntimeError(
                f"Failed while creating plot '{plot_key}' from '{input_path}' "
                f"and saving to '{output_path}'."
            ) from exc


##############################################################################
# INPUT / OUTPUT PATH HELPERS


def build_default_input_paths(plot_keys: Iterable[str]) -> Dict[str, str]:
    """Build default filtered CSV paths for command-line debugging."""
    return {
        plot_key: f"results/filtered/{plot_key}_filtered.csv"
        for plot_key in plot_keys
    }


def build_default_output_paths(
    plot_keys: Iterable[str],
    plot_dir: str,
    plot_extensions: Mapping[str, str],
) -> Dict[str, str]:
    """Build default final plot paths from plot keys and extensions."""
    return {
        plot_key: os.path.join(plot_dir, f"{plot_key}.{plot_extensions[plot_key]}")
        for plot_key in plot_keys
    }


def get_snakemake_paths():
    """Collect paths and config from Snakemake's injected snakemake object."""
    plot_keys = list(snakemake.params.plot_keys)
    config = snakemake.params.config

    input_paths = dict(zip(plot_keys, list(snakemake.input.filtered)))
    output_paths = dict(zip(plot_keys, list(snakemake.output.plots)))
    plot_list_path = snakemake.output.plot_list

    return plot_keys, input_paths, output_paths, plot_list_path, config


def get_cli_paths():
    """Collect paths and config when running this script outside Snakemake."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", required=True, help="Path to config.yaml")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    plot_keys = list(config["plots"]["filter"].keys())
    plot_dir = config["plots"].get("plot_dir", "results/plots/")
    plot_extensions = config["plots"].get("extensions", DEFAULT_PLOT_EXTENSIONS)

    input_paths = build_default_input_paths(plot_keys)
    output_paths = build_default_output_paths(plot_keys, plot_dir, plot_extensions)
    plot_list_path = os.path.join(plot_dir, "plot_list.txt")

    return plot_keys, input_paths, output_paths, plot_list_path, config


##############################################################################
# MAIN WRAPPER


if __name__ == "__main__":
    try:
        snakemake  # noqa: F821
        plot_keys, input_paths, output_paths, plot_list_path, config = get_snakemake_paths()
    except NameError:
        plot_keys, input_paths, output_paths, plot_list_path, config = get_cli_paths()

    run_all_plots(input_paths, output_paths, plot_keys, config)
    write_plot_list(output_paths, plot_list_path)