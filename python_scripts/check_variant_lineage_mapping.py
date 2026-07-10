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

# create variant reference file to check for new variants when new run data comes in
def create_variant_reference(full_df, output_path='results/qc/variant_reference.csv'):
    """
    Create a reference CSV file with unique Variant_name and variant mappings.

    Parameters:
    -----------
    full_df : pandas DataFrame
        Your full_df containing 'Variant_name' and 'variant' columns
    output_path : str
        Where to save the file (default: 'variant_reference.csv')

    Returns:
    --------
    pandas DataFrame
        The reference dataframe that was saved
    """
    # Extract unique Variant_name and variant pairs
    variant_ref = full_df[['Variant_name', 'variant']].drop_duplicates()

    # Sort by Variant_name for easy reference
    variant_ref = variant_ref.sort_values('Variant_name').reset_index(drop=True)

    # Remove any rows where either value is null
    variant_ref = variant_ref.dropna()

    # Save to CSV
    variant_ref.to_csv(output_path, index=False)

    print(f"\n✓ Created {output_path}")
    print(f"  Total unique mappings: {len(variant_ref)}")
    print(f"  Unique Variant_names: {variant_ref['Variant_name'].nunique()}")
    print(f"  Unique CDC variants: {variant_ref['variant'].nunique()}")


    # Check if file already exists
    # Create backup with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = output_path.replace('.csv', f'_backup_{timestamp}.csv')

    # Copy existing file to backup
    existing_df = pd.read_csv(output_path)
    existing_df.to_csv(backup_path, index=False)
    print(f"✓ Backup saved to: {backup_path}")


    return variant_ref

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", required=True, help="path to input file")
    parser.add_argument("--reference", "-r", required=True, help="path to output variant reference list")
    args = parser.parse_args()
    full_df = pd.read_csv(args.input)
    check_variant_lineage_mapping(full_df)
    create_variant_reference(full_df, args.reference)

