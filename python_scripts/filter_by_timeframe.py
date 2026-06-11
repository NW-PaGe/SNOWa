
import yaml
import pandas as pd
from datetime import datetime
from datetime import datetime, timedelta

# function to filter data and generate datasets for plotting the figures
def filter_data_by_timeframe(df, config, plot_name): # CHECK INPUTS
    """
    Filter dataframe based on timeframe specified in config for a specific plot.

    Args:
        df: DataFrame to filter
        config: Full config dictionary loaded from config.yaml
        plot_name: Name of the plot (e.g., 'stacked_bar_plt', 'bubble_plt', etc.)

    Config structure:
        plot_name:
          timeframe: 
            recency: {"value": 6, "unit": "month"}
            OR
            date_range: {"start_date": "2024-01-01", "end_date": "2024-12-31"}
    """
    # Check if plot_name exists in config
    if plot_name not in config:
        raise ValueError(f"Plot '{plot_name}' not found in config")

    plot_config = config[plot_name]

    if 'timeframe' not in plot_config:
        raise ValueError(f"Config for '{plot_name}' must contain 'timeframe' field")

    timeframe = plot_config['timeframe']

    if 'recency' in timeframe:
        recency = timeframe['recency']

        # Validate recency format
        if 'value' not in recency or 'unit' not in recency:
            raise ValueError(
                f"Recency format error in '{plot_name}': Must specify both 'value' and 'unit'. "
                "Example: {'value': 6, 'unit': 'month'}"
            )

        value = recency['value']
        unit = recency['unit']

        # Validate unit (accept both singular and plural forms)
        valid_units = {
            'day': 'days',
            'days': 'days',
            'week': 'weeks',
            'weeks': 'weeks',
            'month': 'months',
            'months': 'months',
            'year': 'years',
            'years': 'years'
        }

        if unit not in valid_units:
            raise ValueError(
                f"Invalid recency unit '{unit}' in '{plot_name}'. "
                f"Valid units are: day, week, month, year (singular or plural)"
            )

        # Normalize to plural form for consistency
        normalized_unit = valid_units[unit]

        # Validate value is numeric
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError(
                f"Recency value must be a positive number in '{plot_name}', got: {value}"
            )

        # Get latest date point in the dataset
        most_recent_date = df['Week'].max()

        # Calculate cutoff date
        if normalized_unit == 'days':
            cutoff_date = most_recent_date - pd.Timedelta(days=value)
        elif normalized_unit == 'weeks':
            cutoff_date = most_recent_date - pd.Timedelta(weeks=value)
        elif normalized_unit == 'months':
            cutoff_date = most_recent_date - pd.DateOffset(months=value)
        elif normalized_unit == 'years':
            cutoff_date = most_recent_date - pd.DateOffset(years=value)

        return df[df['Week'] >= cutoff_date]

    elif 'date_range' in timeframe:
        date_range = timeframe['date_range']

        # Validate date_range format
        if 'start_date' not in date_range or 'end_date' not in date_range:
            raise ValueError(
                f"Date range format error in '{plot_name}': Must specify both 'start_date' and 'end_date'. "
                "Example: {'start_date': '2024-01-01', 'end_date': '2024-12-31'}"
            )

        try:
            start = pd.to_datetime(date_range['start_date'])
            end = pd.to_datetime(date_range['end_date'])
        except Exception as e:
            raise ValueError(
                f"Invalid date format in '{plot_name}'. Use YYYY-MM-DD format. Error: {str(e)}"
            )

        # Validate date logic
        if start > end:
            raise ValueError(
                f"start_date ({start.date()}) cannot be after end_date ({end.date()}) in '{plot_name}'"
            )

        return df[(df['Week'] >= start) & (df['Week'] <= end)]

    else:
        raise ValueError(
            f"Timeframe in '{plot_name}' must contain either 'recency' or 'date_range'. "
            "Examples:\n"
            "  Recency: {'recency': {'value': 6, 'unit': 'month'}}\n"
            "  Date range: {'date_range': {'start_date': '2024-01-01', 'end_date': '2024-12-31'}}"
        )

# create timeframe-filtered dataframes for each of the plots
# parameters are specified in defaults/config.yaml
def prepare_plot_data(weighted_proportions, county_proportions, config):
    """Filter data for multiple plot types based on configuration."""

    plot_configs = [
        (weighted_proportions, 'stacked_bar_plt'),
        (weighted_proportions, 'qc_pa_plt'),
        (weighted_proportions, 'bubble_plt'),
        (weighted_proportions, 'line_plt'),
        (weighted_proportions, 'heatmap_plt'),
        (county_proportions, 'weekly_maps_plt')
    ]

    df_stacked_bar, df_qc_pa, df_bubble, df_line, df_heatmap, df_weekly_maps = [
        filter_data_by_timeframe(df, config, config_key)
        for df, config_key in plot_configs
    ]

    # SAVE DFS

    return df_stacked_bar, df_qc_pa, df_bubble, df_line, df_heatmap, df_weekly_maps

# Usage: # FIX USAGE - NEED TO SAVE DF AS CSV
#df_stacked_bar, df_qc_pa, df_bubble, df_line, df_heatmap, df_weekly_maps = prepare_plot_data(weighted_proportions, county_proportions, config)

# INSERT MAIN WRAPPER
