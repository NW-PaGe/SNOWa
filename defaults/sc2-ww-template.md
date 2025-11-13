# SARS-CoV-2 Wastewater Surveillance Report 

### SARS-CoV-2 Wastewater Surveillance Report Washington State 
### Generated: {{date}}
### Author: {{author}}, {{team}}

#### This report presents comprehensive analysis of SARS-CoV-2 variant detection and proportions in wastewater surveillance data across Washington State.
#### Data Period: {{data_period}} 
#### Analysis Method: Population-weighted proportions by sampling site 

#### Report Contents:

- Weekly population-weighted variant proportions (stacked bar chart) 
- Detection timeline across variants (presence/absence grid)
- Recent trends of top 3 variants (line graph) Variant proportion heatmap ( 10% threshold, past 8 weeks) 
- Geographic distribution maps (dominant variants by county)

#### Key Features:

- Population weighting accounts for sampling site coverage differences 
- Colors match CDC-designated variant hex codes
- Geographic analysis shows spatial patterns of variant circulation 
- Temporal analysis reveals emergence and decline patterns

\pagebreak

![Barplot of SARS-CoV-2 lineages over time](results/plots/barplot.jpeg "Weekly Population-Weighted Variant Proportions")

\pagebreak

### Figure 1: Interpretation
This stacked bar chart shows the relative proportions of different SARS-CoV-2 variants detected in wastewater samples, weighted by the population served by each sampling site. 

Key Features:

- Each bar represents one week of surveillance data 
- Bar segments show the proportion of each variant (colors = CDC hex codes) 
- Population weighting ensures larger communities have appropriate influence 
- Data limited to 2024-2025 due to reliable population data availability 

What This Shows:

- Variant dominance patterns over time 
- Emergence and decline of specific variants 
- Total variant diversity per week 
- Seasonal or temporal circulation patterns 

Public Health Significance:

- Identifies periods of high variant diversity vs. single variant dominance 
- Speed of variant transitions in the community 
- Supports variant-specific public health response planning if necessary
- Provides early warning of emerging variant circulation

\pagebreak

![Weekly Detection Timeline](results/plots/timeline.jpeg "Weekly Detection Timeline")

\pagebreak

### Figure 2: Interpretation 
This grid visualization shows the presence or absence of each variant during specific weeks across the surveillance period. Each colored square indicates detection.

Key Features:

- Colored squares = variant detected that week 
- Empty spaces = variant not detected that week 
- Colors correspond to CDC-designated hex codes 
- Y-axis: all variants detected during surveillance period 
- X-axis: weekly time progression from Jan 2024 - July 2025 

What This Reveals:

- Variant emergence and disappearance patterns
- Co-circulation of multiple variants simultaneously 
- Persistence of variants over extended periods 
- Detection gaps indicating very low circulation or sampling limitations

Surveillance Insights:

- Some variants appear sporadically (possible introductions/imports) 
- Others show sustained circulation over many weeks 
- Gaps between detections may indicate waning circulation 
- New variant emergence often coincides with decline of others

\pagebreak

![Recent Trends of Top 3 Variants](results/plots/top3.jpeg "Top 3 SARS-CoV-2 Variants - Recent 8-Week Trends")

\pagebreak

#### INTERPRETATION: 
This line graph focuses on the three most prevalent variants during the
most recent 8-week period, showing their proportional trends over time.

Key Features:

- Shows only the 3 most abundant variants in recent weeks
- Dynamic selection: variants shown change with each report generation
- Y-axis: proportion of each variant in wastewater Trend lines indicate whether variants are increasing, decreasing, or stable

Clinical Significance:

- Rising trends may indicate emerging dominant variants with transmission advantages 
- Declining trends suggest waning circulation or displacement by other variants 
- Crossing trend lines indicate shifts in variant dominance 
- Steep changes may correlate with transmission advantages or public health interventions 

Possible Surveillance Applications:

- Early detection of rapidly increasing variants 
- Monitoring effectiveness of variant-specific interventions 
- Predicting which variants may become dominant 
- Supporting clinical preparedness for predominant circulating variants 

Note: The specific variants displayed will change with each report based on current surveillance data and recent circulation patterns.

\pagebreak

![Variant Proportion Heatmap](results/plots/heatmap.jpeg "Variant Proportion Heatmap ( 10% Threshold, Past 8 Weeks)")

\pagebreak

### Figure 4: Interpretation 
#### Variant Proportion Heatmap 
This heatmap displays variants that reached 10% proportion in any week during the past 8 weeks. Color intensity represents percentage, with darker blue = higher proportions.

Key Features:

- 10% threshold filter reduces noise from low-abundance detections 
- Numbers in cells show exact percentage values 
- Rows = variants, Columns = weeks (chronological order)
- Color scale: light blue (low %) dark blue (high %) 

Analysis Insights:

- Quick identification of dominant variants by week 
- Comparison of variant proportions across recent surveillance period 
- Detection of rapid changes in variant circulation patterns 
- Focus on variants with meaningful circulation levels 

Public Health Utility:

- Reveals temporal changes in variant proportion estimates 
- Supports resource allocationd for variant-specific public health responses if necessary 
- Tracks temporal patterns that may inform intervention timing if necessary 
- Provides quantitative data for variant surveillance reporting 

Data Quality Notes:

- 10% threshold balances sensitivity with noise reduction 
- Weeks with low overall surveillance may show artificially high percentages 
- Geographic aggregation may mask local hotspots of variant circulation

\pagebreak

![Geographic Distributions](results/plots/n_weeks_map.png "Geographic Distribution: Dominant Variants by County (Past 12 Weeks)")

\pagebreak

### Figure 5: Interpretation
These maps show the dominant SARS-CoV-2 variant in each Washington State
county for recent weeks. Counties are colored according to the variant
with the highest population-weighted proportion in that county for each
specific week. 

Key Features:

- Each map = one week of surveillance data
- Colors match CDC-designated variant hex codes 
- White counties = no surveillance data available 
- "Dominant" = variant with highest weighted proportion (may be \<50% if co-circulation) 

Geographic Insights:

- Spatial patterns of variant circulation across the state 
- Regional differences in variant dominance 
- Spread patterns of emerging variants between counties 
- Geographic clustering or isolation of specific variants 

Important Considerations:

- County-level analysis depends on wastewater sampling site coverage 
- Some counties have limited or no surveillance infrastructure 
- Population weighting accounts for sampling site coverage differences 
- Surveillance gaps may create apparent geographic boundaries 

Public Health Applications:

- Regional variant-specific public health messaging and interventions if necessary 
- Identification of counties with emerging variant circulation 
- Support for regional surveillance strategy and sampling prioritization 
- Early warning system for variant spread patterns

Surveillance Strategy Implications:

- Counties with persistent "no data" status may need enhanced sampling 
- Geographic clustering suggests local transmission networks 
- Rapid geographic spread may indicate highly transmissible variants

\pagebreak

# Summary

Overview: 
This report analyzes SARS-CoV-2 wastewater surveillance data from Washington State covering January 2024
through July 2025. All analyses use population-weighted proportions to
account for differences in sampling site population coverage. 

Methodology:

- Population weighting ensures representative analysis across sampling sites 
- Weekly temporal aggregation reduces day-to-day variation in measurements 
- Geographic analysis determines county-level dominant variants 
- Statistical filtering (10% threshold) focuses on variants with meaningful circulation 

Surveillance Strengths:

- Early detection of variant emergence before clinical surveillance 
- Population-level sampling independent of healthcare-seeking behavior 
- Geographic coverage across multiple counties in Washington State
- Consistent methodology enabling temporal trend analysis 

Current Limitations:

- Population data availability constrains analysis to 2024-2025 period 
- Population weighting assumes even distribution of residents within sampling regions 
- Sampling frequency is not consistent across weeks or sites 
- Many counties have only one sampling site that may not represent the entire county population 
- Sewer shed coverage may only represents the specific populations served 
- Several counties across Washington State are not sampled, limiting statewide representativeness
- Stacked proportions and geographic maps may not reflect variant circulation in unsampled counties or regions 
- County-level analysis quality depends on sampling site distribution and coverage 
- Wastewater surveillance may not capture all community transmission patterns
- Detection sensitivity can vary by variant and laboratory analytical methods 

How to read this report: 

The figures work together to tell a complete story. If you see a new color appearing in the stacked bars, you can:

1. Check the maps to see if it is a dominant variant in a specific county 
2. Look at the timeline to see if it's been detected before 
3. Use the heatmap to see if it's above 10% anywhere

\pagebreak

## Methods 
**Population Weighting**: For each sampling site and week, average
variant proportions were calculated per sample site per week, then
multiplied by the population served by that wastewater treatment plant.
Weekly state-level proportions were calculated by summing
population-weighted contributions from all sites and dividing by total
population served. This approach prevents over-representation of smaller sites and under-representation of larger population centers. 

**Stacked Bar Chart (Weekly Variant Proportions)**: Population-weighted proportions were
pivoted into a wide-format table with weeks as rows and variants as
columns. The pivot table was plotted using matplotlib's stacked bar
chart function with CDC hex codes for colors. 

**Timeline (Variant Detection)**: Created a binary presence matrix by grouping data by variant and week, then converted counts to 1 (present) or 0 (absent). Used matplotlib scatter plot with square markers (marker='s') colored by CDC hex codes. 

**Line Graph (Top 3 Variants)**: Calculated mean proportions for
each variant over the most recent 8 weeks, sorted in descending order
and selected top 3. Filtered data to these variants and recent weeks,
then used matplotlib plot function with CDC hex colors. 

**Heatmap (High-Prevalence Variants)**: Filtered data to variants with maximum proportion 10% in any week during past 8 weeks. Created pivot table with variants as rows and weeks as columns, then applied seaborn heatmap function with 'Blues' colormap. 

**County Maps (Dominant Variants)**: Merged
wastewater data with Washington State county shapefiles using geopandas. For each county-week combination, identified variant with highest weighted proportion using pandas groupby and idxmax functions. Created 12 subplot maps using matplotlib GridSpec, colored counties by dominant variant hex codes, and set empty counties to white (#FFFFFF).

## Contact Information 
For technical questions about methodology, data
interpretation, or surveillance recommendations, contact: {{author}}: {{author_email}} ; {{team}}: {{team_email}}