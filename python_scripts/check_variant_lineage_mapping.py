import pandas as pd
import argparse
import os
from datetime import datetime

def check_variant_lineage_mapping(full_df):
    """
    QC check to identify Variant_name entries without corresponding variant (parent) assignments,
    missing hex_code values, and flag Recombinant/Ancestral classifications.

    Parameters:
    full_df: DataFrame containing 'Variant_name', 'variant', and 'hex_code' columns

    Returns:
    dict: Summary of mapping issues
    """
    print("=== VARIANT LINEAGE MAPPING QC CHECK ===\n")

    # Check for Variant_name entries with missing variant (parent) data
    missing_parent = full_df[full_df['variant'].isnull() & full_df['Variant_name'].notna()]

    if len(missing_parent) > 0:
        orphaned_variants = missing_parent['Variant_name'].unique()
        print(f"WARNING: {len(orphaned_variants)} Variant_name entries lack parent lineage assignment:")

        # Show counts for each orphaned variant
        orphan_counts = missing_parent['Variant_name'].value_counts()
        for variant_name, count in orphan_counts.items():
            print(f"   - {variant_name}: {count} samples")

        # Show sample data for investigation
        print(f"\n   Sample records with missing parent assignments:")
        sample_records = missing_parent[['Lab_ID', 'Sample_Site', 'Variant_name', 'variant']].head(5)
        for _, row in sample_records.iterrows():
            print(f"   - Lab_ID: {row['Lab_ID']}, Site: {row['Sample_Site']}, Variant_name: {row['Variant_name']}")

    else:
        print("All Variant_name entries have corresponding parent lineage assignments")

    # Check for missing hex_code values - show both Variant_name and variant
    missing_hex = full_df[full_df['hex_code'].isnull() & full_df['Variant_name'].notna()]

    if len(missing_hex) > 0:
        print(f"\nWARNING: {len(missing_hex)} records lack hex_code assignment:")

        # Get unique combinations of Variant_name and variant that are missing hex codes
        missing_hex_combos = missing_hex[['Variant_name', 'variant']].drop_duplicates()
        print(f"   {len(missing_hex_combos)} unique Variant_name/variant combinations missing hex codes:")

        for _, row in missing_hex_combos.iterrows():
            variant_name = row['Variant_name']
            variant = row['variant'] if pd.notna(row['variant']) else 'NO_PARENT'
            count = len(missing_hex[(missing_hex['Variant_name'] == variant_name) & 
                                   (missing_hex['variant'] == row['variant'])])
            print(f"   - Variant_name: {variant_name} | variant: {variant} | {count} samples")

        print(f"\n   These entries will cause visualization issues - check lineage classification file")

    else:
        print("\nAll Variant_name entries have corresponding hex_code assignments")

    # Check for Recombinant variants
    recombinant_variants = full_df[full_df['variant'] == 'Recombinant']

    if len(recombinant_variants) > 0:
        recombinant_names = recombinant_variants['Variant_name'].unique()
        print(f"\nINFO: {len(recombinant_names)} Variant_name entries classified as Recombinant:")

        recombinant_counts = recombinant_variants['Variant_name'].value_counts()
        for variant_name, count in recombinant_counts.items():
            print(f"   - {variant_name}: {count} samples")

    else:
        print("\nNo Recombinant variants detected")

    # Check for Ancestral variants  
    ancestral_variants = full_df[full_df['variant'] == 'Ancestral']

    if len(ancestral_variants) > 0:
        ancestral_names = ancestral_variants['Variant_name'].unique()
        print(f"\nWARNING: {len(ancestral_names)} Variant_name entries classified as Ancestral:")

        ancestral_counts = ancestral_variants['Variant_name'].value_counts()
        for variant_name, count in ancestral_counts.items():
            print(f"   - {variant_name}: {count} samples")

        print("   Ancestral variants in recent data may indicate contamination or misclassification")

    else:
        print("\nNo Ancestral variants detected")

    # Summary statistics
    total_variant_names = full_df['Variant_name'].nunique()
    mapped_variants = full_df[full_df['variant'].notna()]['Variant_name'].nunique()
    hex_mapped_variant_names = full_df[full_df['hex_code'].notna()]['Variant_name'].nunique()

    mapping_rate = (mapped_variants / total_variant_names) * 100 if total_variant_names > 0 else 0
    hex_mapping_rate = (hex_mapped_variant_names / total_variant_names) * 100 if total_variant_names > 0 else 0

    print(f"\n=== MAPPING SUMMARY ===")
    print(f"Total unique Variant_name entries: {total_variant_names}")
    print(f"Successfully mapped to parent lineages: {mapped_variants}")
    print(f"Successfully mapped to hex codes: {hex_mapped_variant_names}")
    print(f"Parent lineage mapping rate: {mapping_rate:.1f}%")
    print(f"Hex code mapping rate: {hex_mapping_rate:.1f}%")
    print(f"Recombinant variants detected: {len(recombinant_variants)}")
    print(f"Ancestral variants detected: {len(ancestral_variants)}")

    if mapping_rate < 95:
        print("WARNING: Parent mapping rate below 95% - investigate lineage classification file")
    if hex_mapping_rate < 95:
        print("WARNING: Hex code mapping rate below 95% - investigate lineage classification file")

    # Return summary for programmatic use
    return {
        'orphaned_variant_names': orphaned_variants.tolist() if len(missing_parent) > 0 else [],
        'missing_hex_combinations': missing_hex_combos.to_dict('records') if len(missing_hex) > 0 else [],
        'recombinant_variant_names': recombinant_names.tolist() if len(recombinant_variants) > 0 else [],
        'ancestral_variant_names': ancestral_names.tolist() if len(ancestral_variants) > 0 else [],
        'orphan_count': len(missing_parent),
        'missing_hex_count': len(missing_hex),
        'recombinant_count': len(recombinant_variants),
        'ancestral_count': len(ancestral_variants),
        'mapping_rate': mapping_rate,
        'hex_mapping_rate': hex_mapping_rate,
        'total_variant_names': total_variant_names,
        'mapped_variants': mapped_variants,
        'hex_mapped_variant_names': hex_mapped_variant_names
    }

# create/update variant reference file to check for new variants when new run data comes in
def create_variant_reference(full_df, output_path='defaults/variant_reference.csv'):
    """
    Create or update a cumulative variant reference file.

    Existing historical Variant_name entries are preserved.
    Current classifications override older classifications for the same Variant_name.
    Reclassifications and newly observed Variant_name entries are reported and saved.

    Parameters:
    -----------
    full_df : pandas DataFrame
        DataFrame containing 'Variant_name' and 'variant' columns.

    output_path : str
        Path to the current variant reference file.

    Returns:
    --------
    pandas DataFrame
        Updated variant reference dataframe.
    """

    date_stamp = datetime.now().strftime('%Y%m%d')

    print("\n=== VARIANT REFERENCE UPDATE ===")

    # --------------------------------------------------
    # 1. BUILD CURRENT MAPPINGS
    # --------------------------------------------------
    current_ref = (
        full_df[['Variant_name', 'variant']]
        .dropna()
        .drop_duplicates()
        .reset_index(drop=True)
    )

    print(f"Current dataset mappings: {len(current_ref)}")
    print(
        f"Current unique Variant_names: "
        f"{current_ref['Variant_name'].nunique()}"
    )

    # --------------------------------------------------
    # 2. CHECK CURRENT DATA FOR MULTIPLE CLASSIFICATIONS
    # --------------------------------------------------
    current_counts = (
        current_ref.groupby('Variant_name')['variant']
        .nunique()
    )

    current_duplicates = current_counts[current_counts > 1]

    if len(current_duplicates) > 0:
        print(
            f"\nWARNING: {len(current_duplicates)} Variant_name entries "
            "have multiple classifications in the current data:"
        )

        for variant_name in current_duplicates.index:
            mappings = current_ref.loc[
                current_ref['Variant_name'] == variant_name,
                'variant'
            ].tolist()

            print(
                f"   - {variant_name}: "
                f"{' | '.join(map(str, mappings))}"
            )

        print(
            "\nNOTE: Current classifications will take priority during "
            "the reference update."
        )

    else:
        print(
            "\n✓ Current data contains one classification per Variant_name"
        )

    # --------------------------------------------------
    # 3. IF AN EXISTING REFERENCE EXISTS, BACK IT UP
    # --------------------------------------------------
    if os.path.exists(output_path):

        existing_df = pd.read_csv(output_path)

        existing_df = (
            existing_df[['Variant_name', 'variant']]
            .dropna()
            .drop_duplicates()
            .reset_index(drop=True)
        )

        print(
            f"\nExisting reference mappings: {len(existing_df)}"
        )
        print(
            f"Existing unique Variant_names: "
            f"{existing_df['Variant_name'].nunique()}"
        )

        backup_path = (
            f"results/qc/variant_reference_backup_{date_stamp}.csv"
        )

        existing_df.to_csv(backup_path, index=False)

        print(f"✓ Backup saved to: {backup_path}")

        # --------------------------------------------------
        # 4. CHECK EXISTING REFERENCE FOR DUPLICATE MAPPINGS
        # --------------------------------------------------
        existing_counts = (
            existing_df.groupby('Variant_name')['variant']
            .nunique()
        )

        existing_duplicates = existing_counts[existing_counts > 1]

        if len(existing_duplicates) > 0:

            print(
                f"\nWARNING: {len(existing_duplicates)} Variant_name "
                "entries have multiple classifications in the "
                "existing reference:"
            )

            for variant_name in existing_duplicates.index:
                mappings = existing_df.loc[
                    existing_df['Variant_name'] == variant_name,
                    'variant'
                ].tolist()

                print(
                    f"   - {variant_name}: "
                    f"{' | '.join(map(str, mappings))}"
                )

        else:
            print(
                "\n✓ Existing reference contains one classification "
                "per Variant_name"
            )

        # --------------------------------------------------
        # 5. COMPARE OLD VS CURRENT CLASSIFICATIONS
        # --------------------------------------------------

        # Reduce current mappings to one row per Variant_name.
        # The current classification will be treated as authoritative.
        current_unique = (
            current_ref
            .drop_duplicates(subset=['Variant_name'], keep='last')
            .reset_index(drop=True)
        )

        # For comparison, reduce existing reference to one row per Variant_name.
        existing_unique = (
            existing_df
            .drop_duplicates(subset=['Variant_name'], keep='last')
            .reset_index(drop=True)
        )

        comparison = existing_unique.merge(
            current_unique,
            on='Variant_name',
            how='outer',
            suffixes=('_old', '_new'),
            indicator=True
        )

        # Newly observed Variant_names
        new_variants = comparison[
            comparison['_merge'] == 'right_only'
        ].copy()

        # Existing Variant_names whose classification changed
        reclassified = comparison[
            (comparison['_merge'] == 'both') &
            (comparison['variant_old'] != comparison['variant_new'])
        ].copy()

        # Unchanged mappings
        unchanged = comparison[
            (comparison['_merge'] == 'both') &
            (comparison['variant_old'] == comparison['variant_new'])
        ].copy()

        print("\n=== REFERENCE COMPARISON ===")
        print(f"New Variant_names: {len(new_variants)}")
        print(f"Reclassified Variant_names: {len(reclassified)}")
        print(f"Unchanged Variant_names: {len(unchanged)}")

        # --------------------------------------------------
        # 6. REPORT NEW VARIANTS
        # --------------------------------------------------
        if len(new_variants) > 0:

            print("\nNEW VARIANT_NAMES:")

            for _, row in new_variants.iterrows():
                print(
                    f"   - {row['Variant_name']} "
                    f"→ {row['variant_new']}"
                )

            new_variants_output = new_variants[
                ['Variant_name', 'variant_new']
            ].rename(
                columns={'variant_new': 'variant'}
            )

            new_variants_path = (
                f"results/qc/new_variant_mappings_{date_stamp}.csv"
            )

            new_variants_output.to_csv(
                new_variants_path,
                index=False
            )

            print(
                f"✓ New variant mappings saved to: "
                f"{new_variants_path}"
            )

        else:
            print("\n✓ No new Variant_name mappings detected")

        # --------------------------------------------------
        # 7. REPORT RECLASSIFICATIONS
        # --------------------------------------------------
        if len(reclassified) > 0:

            print("\nRECLASSIFICATIONS DETECTED:")

            for _, row in reclassified.iterrows():
                print(
                    f"   - {row['Variant_name']}: "
                    f"{row['variant_old']} "
                    f"→ {row['variant_new']} "
                    f"(using {row['variant_new']})"
                )

            reclassification_output = reclassified[
                [
                    'Variant_name',
                    'variant_old',
                    'variant_new'
                ]
            ].rename(
                columns={
                    'variant_old': 'old_variant',
                    'variant_new': 'new_variant'
                }
            )

            reclassification_output['updated_variant'] = (
                reclassification_output['new_variant']
            )

            reclassification_path = (
                f"results/qc/"
                f"variant_reclassifications_{date_stamp}.csv"
            )

            reclassification_output.to_csv(
                reclassification_path,
                index=False
            )

            print(
                f"✓ Reclassification report saved to: "
                f"{reclassification_path}"
            )

        else:
            print("\n✓ No lineage reclassifications detected")

        # --------------------------------------------------
        # 8. UPDATE REFERENCE
        #
        # Preserve historical Variant_names that are not in
        # current data, but current classifications override
        # historical classifications when Variant_name matches.
        # --------------------------------------------------

        historical_only = existing_unique[
            ~existing_unique['Variant_name'].isin(
                current_unique['Variant_name']
            )
        ]

        variant_ref = pd.concat(
            [
                historical_only,
                current_unique
            ],
            ignore_index=True
        )

    else:
        # --------------------------------------------------
        # NO EXISTING REFERENCE
        # --------------------------------------------------
        print(
            f"\nNo existing reference found at {output_path}"
        )
        print(
            "Creating a new reference from the current dataset."
        )

        variant_ref = (
            current_ref
            .drop_duplicates(
                subset=['Variant_name'],
                keep='last'
            )
            .reset_index(drop=True)
        )

    # --------------------------------------------------
    # 9. FINAL VALIDATION
    # --------------------------------------------------
    variant_ref = (
        variant_ref
        .dropna()
        .sort_values('Variant_name')
        .reset_index(drop=True)
    )

    final_duplicates = (
        variant_ref['Variant_name']
        .duplicated()
        .sum()
    )

    print("\n=== FINAL REFERENCE VALIDATION ===")
    print(f"Total mappings: {len(variant_ref)}")
    print(
        f"Unique Variant_names: "
        f"{variant_ref['Variant_name'].nunique()}"
    )
    print(
        f"Unique parent variants: "
        f"{variant_ref['variant'].nunique()}"
    )
    print(
        f"Duplicate Variant_name entries remaining: "
        f"{final_duplicates}"
    )

    if final_duplicates == 0:
        print(
            "✓ Final reference contains one classification "
            "per Variant_name"
        )
    else:
        print(
            "WARNING: Duplicate Variant_name entries remain "
            "in the final reference"
        )

    # --------------------------------------------------
    # 10. SAVE UPDATED REFERENCE
    # --------------------------------------------------
    variant_ref.to_csv(output_path, index=False)

    print(f"\n✓ Updated reference saved to: {output_path}")

    return variant_ref

    # Sort by Variant_name for easy reference
    variant_ref = (
        variant_ref
        .sort_values('Variant_name')
        .reset_index(drop=True)
    )

    # Save updated cumulative reference
    variant_ref.to_csv(output_path, index=False)

    print(f"\n✓ Updated {output_path}")
    print(f"  Total unique mappings: {len(variant_ref)}")
    print(f"  Unique Variant_names: {variant_ref['Variant_name'].nunique()}")
    print(f"  Unique CDC variants: {variant_ref['variant'].nunique()}")

    return variant_ref

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="path to input file")
    parser.add_argument("--reference", "-r", required=True, help="path to output variant reference list")
    args = parser.parse_args()
    full_df = pd.read_csv(args.input)
    check_variant_lineage_mapping(full_df)
    create_variant_reference(full_df, args.reference)

