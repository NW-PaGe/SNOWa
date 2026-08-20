# 2  Add sample site and lineage classifications file
# adding sample site locations and lineage classifications

import pandas as pd
import argparse
from datetime import date

def map_metadata(sites, classifications, input, output):
    """
    Add sample site locations and lineage classifications to combined dataframe.

    Duplicate lineage classifications are resolved in memory before merging.
    The original lineage classification file is not modified.

    Resolution order:
    1. If a usable 'status' column is present, prefer 'active' over 'withdrawn'.
    2. If status is unavailable or cannot uniquely resolve the duplicate,
       use the alphabetically later wastewater_variant_name as a fallback.
    3. Output all duplicate classifications, the resolution method used,
       retained mapping, and discarded mapping(s) to results/qc/.
    """

    # --------------------------------------------------
    # LOAD INPUT FILES
    # --------------------------------------------------

    try:
        lineage_classifications = pd.read_csv(classifications)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Lineage classifications file not found: {classifications}"
        )

    try:
        sample_sites = pd.read_csv(sites)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Sample sites file not found: {sites}"
        )

    try:
        combined_df = pd.read_csv(input)
    except FileNotFoundError:
        raise FileNotFoundError(
            f"Data file not found: {input}"
        )

    # --------------------------------------------------
    # CHECK AND RESOLVE DUPLICATE LINEAGE CLASSIFICATIONS
    # --------------------------------------------------

    # Work on a copy so the source LCF is never modified
    lineage_classifications_clean = lineage_classifications.copy()

    duplicate_mask = lineage_classifications_clean.duplicated(
        subset=['lineage_extracted'],
        keep=False
    )

    duplicate_lcf = lineage_classifications_clean[duplicate_mask]

    # Store all duplicate-resolution details for QC output
    duplicate_resolution_records = []

    if not duplicate_lcf.empty:

        duplicate_lineages = duplicate_lcf[
            'lineage_extracted'
        ].unique()

        print("\n=== DUPLICATE LINEAGE CLASSIFICATION CHECK ===")
        print(
            f"WARNING: Found {len(duplicate_lineages)} "
            "lineage_extracted value(s) with multiple classifications."
        )

        resolved_rows = []

        # Rows that do not need resolution remain unchanged
        non_duplicate_rows = lineage_classifications_clean[
            ~duplicate_mask
        ].copy()

        for lineage in duplicate_lineages:

            group = lineage_classifications_clean[
                lineage_classifications_clean[
                    'lineage_extracted'
                ] == lineage
            ].copy()

            print(f"\nDuplicate lineage_extracted: {lineage}")
            print("Classifications found:")

            for _, row in group.iterrows():

                classification = row[
                    'wastewater_variant_name'
                ]

                hex_code = row.get(
                    'hex_code',
                    'N/A'
                )

                if 'status' in group.columns:
                    status = row.get(
                        'status',
                        'N/A'
                    )

                    print(
                        f"   - {classification}"
                        f" | status: {status}"
                        f" | hex_code: {hex_code}"
                    )

                else:
                    print(
                        f"   - {classification}"
                        f" | hex_code: {hex_code}"
                    )

            # ------------------------------------------
            # PRIMARY RESOLUTION: STATUS
            # ------------------------------------------

            retained_row = None
            resolution_method = None

            if 'status' in group.columns:

                status_normalized = (
                    group['status']
                    .astype(str)
                    .str.strip()
                    .str.lower()
                )

                active_rows = group[
                    status_normalized == 'active'
                ]

                withdrawn_rows = group[
                    status_normalized == 'withdrawn'
                ]

                # Use status only if it uniquely identifies
                # one active classification
                if (
                    len(active_rows) == 1
                    and len(withdrawn_rows) >= 1
                ):
                    retained_row = active_rows.iloc[0]
                    resolution_method = (
                        "status field: active preferred "
                        "over withdrawn"
                    )

            # ------------------------------------------
            # FALLBACK: ALPHABETICAL CLASSIFICATION
            # ------------------------------------------

            if retained_row is None:

                group_sorted = group.sort_values(
                    'wastewater_variant_name'
                )

                retained_row = group_sorted.iloc[-1]

                if 'status' in group.columns:
                    resolution_method = (
                        "alphabetical fallback: "
                        "status did not uniquely resolve duplicate"
                    )
                else:
                    resolution_method = (
                        "alphabetical fallback: "
                        "status column not present"
                    )

            retained_classification = retained_row[
                'wastewater_variant_name'
            ]

            discarded = group[
                group.index != retained_row.name
            ]

            print(
                f"Resolution method: {resolution_method}"
            )

            print(
                f"Retained: {retained_classification}"
            )

            if not discarded.empty:

                discarded_values = discarded[
                    'wastewater_variant_name'
                ].tolist()

                print(
                    "Discarded: "
                    + ", ".join(
                        map(str, discarded_values)
                    )
                )

            if "alphabetical fallback" in resolution_method:
                print(
                    "WARNING: Alphabetical fallback was used. "
                    "Review the lineage classification file "
                    "if this resolution is incorrect."
                )

            # ------------------------------------------
            # RECORD ALL DUPLICATE ROWS FOR QC OUTPUT
            # ------------------------------------------

            for idx, row in group.iterrows():

                duplicate_resolution_records.append({
                    'lineage_extracted':
                        lineage,

                    'wastewater_variant_name':
                        row['wastewater_variant_name'],

                    'status':
                        row.get('status', 'N/A'),

                    'hex_code':
                        row.get('hex_code', 'N/A'),

                    'resolution_method':
                        resolution_method,

                    'retained':
                        idx == retained_row.name,

                    'retained_classification':
                        retained_classification
                })

            resolved_rows.append(
                retained_row
            )

        # ----------------------------------------------
        # CREATE CLEANED IN-MEMORY CLASSIFICATION TABLE
        # ----------------------------------------------

        resolved_duplicates = pd.DataFrame(
            resolved_rows
        )

        lineage_classifications_clean = pd.concat(
            [
                non_duplicate_rows,
                resolved_duplicates
            ],
            ignore_index=True
        )

        # ----------------------------------------------
        # SAVE DUPLICATE QC REPORT
        # ----------------------------------------------

        date_stamp = date.today().strftime(
            '%Y%m%d'
        )

        duplicate_output = (
            "results/qc/"
            f"lineage_classification_duplicates_{date_stamp}.csv"
        )

        duplicate_resolution_df = pd.DataFrame(
            duplicate_resolution_records
        )

        duplicate_resolution_df.to_csv(
            duplicate_output,
            index=False
        )

        print(
            f"\n✓ Duplicate classification QC saved to: "
            f"{duplicate_output}"
        )

        print(
            "✓ Duplicate lineage classifications "
            "resolved in memory"
        )

    else:
        print(
            "\n✓ No duplicate lineage_extracted values "
            "detected in lineage classification file"
        )

    # --------------------------------------------------
    # VALIDATE CLEANED CLASSIFICATION DATA
    # --------------------------------------------------

    remaining_duplicates = (
        lineage_classifications_clean[
            lineage_classifications_clean.duplicated(
                subset=['lineage_extracted'],
                keep=False
            )
        ]
    )

    if not remaining_duplicates.empty:

        print(
            "\nWARNING: Duplicate lineage_extracted values "
            "remain after resolution:"
        )

        print(
            remaining_duplicates[
                [
                    'lineage_extracted',
                    'wastewater_variant_name'
                ]
            ].to_string(index=False)
        )

    else:
        print(
            "\n✓ Classification data contains one row per "
            "lineage_extracted after resolution"
        )

    # --------------------------------------------------
    # WORKING WITH DATES
    # --------------------------------------------------

    combined_df[
        'Sample_Collection_Date'
    ] = pd.to_datetime(
        combined_df[
            'Sample_Collection_Date'
        ]
    )

    combined_df['Week'] = (
        combined_df[
            'Sample_Collection_Date'
        ]
        .dt.to_period('W-MON')
        .dt.start_time
        .dt.date
    )

    combined_df['Week'] = pd.to_datetime(
        combined_df['Week']
    )

    # --------------------------------------------------
    # ADD LINEAGE CLASSIFICATIONS
    # --------------------------------------------------

    full_df = combined_df.merge(
        lineage_classifications_clean[
            [
                'wastewater_variant_name',
                'lineage_extracted',
                'hex_code'
            ]
        ],
        how='left',
        left_on='Variant_name',
        right_on='lineage_extracted'
    ).rename(
        columns={
            'wastewater_variant_name':
                'variant'
        }
    )

    # --------------------------------------------------
    # ADD SAMPLE SITES
    # --------------------------------------------------

    full_df = full_df.merge(
        sample_sites[
            [
                'Sample_Site',
                'county',
                'population'
            ]
        ],
        how='left',
        on='Sample_Site'
    )

    full_df['population'] = (
        full_df['population']
        .round()
    )

    # --------------------------------------------------
    # DOWNSTREAM DUPLICATE CHECK
    # --------------------------------------------------

    duplicates = full_df[
        full_df.duplicated(
            subset=[
                'Sample_ID',
                'variant'
            ],
            keep=False
        )
    ]

    if not duplicates.empty:

        print(
            f"\n⚠️ Warning: Found {len(duplicates)} "
            "duplicate rows for same Sample_ID and variant"
        )

    else:
        print(
            "\n✓ No duplicate rows found for "
            "same Sample_ID and variant"
        )

    # --------------------------------------------------
    # DROP VALIDATION DATA
    # --------------------------------------------------

    full_df = full_df[
        ~full_df[
            'Lab_ID'
        ].str.contains(
            'WWVal|positive|negative|control',
            case=False,
            na=False
        )
    ]

    # --------------------------------------------------
    # SAVE FINAL OUTPUT
    # --------------------------------------------------

    full_df.to_csv(
        output,
        index=False
    )

    print(
        "✅ Mapping complete. "
        "Results saved as " + output
    )

    return full_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sites", "-s", required=True, help="Path to Sample Sites csv")
    parser.add_argument("--classifications", "-c", required=True, help="Path to lineage classifications csv file")
    parser.add_argument("--input", "-i", required=True, help="Path to deduplicated data")
    parser.add_argument("--output", "-o", required=True, help="Path to output file")
    args = parser.parse_args()

    map_metadata(args.sites, args.classifications, args.input, args.output)
