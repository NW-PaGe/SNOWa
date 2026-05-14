import pandas as pd
import argparse
from pathlib import Path


def metadata_qc(input_path, output_csv, output_txt):
    """
    QC check for duplicate Sample_IDs across multiple sequencing runs.
    Detects same sample processed with different Freyja database versions.
    Always deduplicates by earliest Sample_Collection_Date.

    Args:
        input_path: path to combined dataframe CSV
        output_csv: path for deduplicated CSV output
        output_txt: path for console log output
    """
    
    # Setup log capture
    log_lines = []
    def log(msg=""):
        print(msg)
        log_lines.append(msg)
    
    # Create output directories if needed
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    Path(output_txt).parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load data
        raw_combined_df = pd.read_csv(input_path)
        
        log("=== METADATA QC - DUPLICATE LAB_ID CHECK ===\n")

        if 'source_file' not in raw_combined_df.columns:
            log("❌ 'source_file' column not found - was process_data() run correctly?")
            Path(output_txt).write_text("\n".join(log_lines))
            raise ValueError("Missing 'source_file' column in raw_combined_df")

        # Find Sample_IDs that appear in more than one source file
        lab_source = raw_combined_df[['Sample_ID', 'source_file']].drop_duplicates()
        lab_file_counts = lab_source.groupby('Sample_ID')['source_file'].count()
        duplicate_sample_ids = lab_file_counts[lab_file_counts > 1].index.tolist()

        if not duplicate_sample_ids:
            log("✅ No duplicate Sample_IDs found across source files")
            log(f"   {raw_combined_df['Sample_ID'].nunique()} unique Sample_IDs across {raw_combined_df['source_file'].nunique()} source file(s)")
            log("\n   DEBUG — All Sample_IDs and their source files:")
            for lab_id, group in raw_combined_df.groupby('Sample_ID')['source_file'].unique().items():
                log(f"   • {lab_id}: {', '.join(sorted(group))}")
            
            # No dedup needed, save original data
            raw_combined_df.to_csv(output_csv, index=False)
            log(f"\n💾 Saved combined data to {output_csv}")
            log(f"💾 Saved QC log to {output_txt}")
            Path(output_txt).write_text("\n".join(log_lines))
            return

        log(f"⚠️  WARNING: {len(duplicate_sample_ids)} Sample_ID(s) appear in multiple source files\n")
        log(f"{'Sample_ID':<20} {'Field':<25} {'Consistent?':<15} {'Values'}")
        log("-" * 90)

        fields_to_compare = ['Sample_ID', 'Sample_Site', 'Sample_Collection_Date']
        resolution_needed = []

        for lab_id in duplicate_sample_ids:
            lab_data = raw_combined_df[raw_combined_df['Sample_ID'] == lab_id]
            source_files = lab_data['source_file'].unique()

            log(f"\n🔬 Sample_ID: {lab_id}")
            log(f"   Found in {len(source_files)} source file(s): {', '.join(sorted(source_files))}")

            # Compare metadata fields
            all_consistent = True
            for field in fields_to_compare:
                if field in lab_data.columns:
                    unique_vals = lab_data[field].dropna().unique()
                    is_consistent = len(unique_vals) == 1
                    if not is_consistent:
                        all_consistent = False
                    status = "✅ MATCH" if is_consistent else "❌ MISMATCH"
                    val_display = unique_vals[0] if is_consistent else " | ".join(str(v) for v in unique_vals)
                    log(f"   {field:<25} {status:<15} {val_display}")
                else:
                    log(f"   {field:<25} {'⚠️ MISSING':<15} Column not found")

            # Variant compositions will always differ - just report, don't flag as mismatch
            variant_counts = lab_data.groupby('source_file')['Variant_name'].nunique()
            log(f"   {'Variant composition':<25} {'ℹ️  DIFFERS':<15} (expected — different Freyja DB versions)")
            for src, count in variant_counts.items():
                log(f"      • {src}: {count} unique variants")

            if not all_consistent:
                log(f"   🔴 METADATA MISMATCH — manual review required before proceeding")
            else:
                log(f"   🟡 Metadata consistent — duplicate is likely a re-run with updated database")

            resolution_needed.append({
                'lab_id': lab_id,
                'source_files': sorted(source_files),
                'metadata_consistent': all_consistent
            })

        # Determine if any hard mismatches exist
        hard_mismatches = [r for r in resolution_needed if not r['metadata_consistent']]

        log("\n" + "=" * 60)
        log("DUPLICATE LAB_ID SUMMARY")
        log("=" * 60)
        log(f"   Total duplicate Sample_IDs:        {len(duplicate_sample_ids)}")
        log(f"   Metadata-consistent re-runs:    {len(resolution_needed) - len(hard_mismatches)}")
        log(f"   Hard metadata mismatches:       {len(hard_mismatches)}")

        if hard_mismatches:
            log(f"\n🔴 HARD MISMATCHES DETECTED — proceeding with dedup, FLAGGED for review:")
            for r in hard_mismatches:
                log(f"   • {r['lab_id']}")
            log("\n   These Sample_IDs have conflicting Sample_ID, Sample_Site, or Collection_Date.")
            log("   Review output log and resolve in source files if needed.")

        log(f"\n🎯 RESOLUTION: Keep earliest run per Sample_ID")
        log(f"   (Earliest = oldest Sample_Collection_Date — RNA degrades over time, earlier run has more genetic material)")

        # Always dedup - Keep only rows from the earliest Sample_Collection_Date per Sample_ID
        raw_combined_df['_collection_date'] = pd.to_datetime(raw_combined_df['Sample_Collection_Date'], errors='coerce')
        min_date = raw_combined_df.groupby('Sample_ID')['_collection_date'].transform('min')
        combined_df = raw_combined_df[raw_combined_df['_collection_date'] == min_date].drop(columns='_collection_date')

        removed = len(raw_combined_df) - len(combined_df)
        log(f"\n✅ Deduplication complete")
        log(f"   Rows before: {len(raw_combined_df)}")
        log(f"   Rows removed: {removed}")
        log(f"   Rows after:  {len(combined_df)}")
        log(f"\n   Dropped source files per Sample_ID:")
        for sample_id in duplicate_sample_ids:
            sample_data = raw_combined_df[raw_combined_df['Sample_ID'] == sample_id].copy()
            sample_data['_collection_date'] = pd.to_datetime(sample_data['Sample_Collection_Date'], errors='coerce')
            earliest = sample_data['_collection_date'].min()
            kept = sample_data[sample_data['_collection_date'] == earliest]['source_file'].iloc[0]
            dropped = sorted(sample_data[sample_data['_collection_date'] != earliest]['source_file'].unique())
            log(f"   • {sample_id}: kept {kept} ({earliest.date()}) | dropped {', '.join(dropped)}")

        # Write outputs
        combined_df.to_csv(output_csv, index=False)
        log(f"\n💾 Saved deduplicated data to {output_csv}")
        log(f"💾 Saved QC log to {output_txt}")
        Path(output_txt).write_text("\n".join(log_lines))

    except Exception as e:
        # Make sure we capture any errors in the log
        log(f"\n❌ ERROR: {str(e)}")
        Path(output_txt).write_text("\n".join(log_lines))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Metadata QC and deduplication for wastewater sequencing data")
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--output-csv", required=True, help="Path for deduplicated CSV output")
    parser.add_argument("--output-txt", required=True, help="Path for console log output")
    args = parser.parse_args()
    
    metadata_qc(args.input, args.output_csv, args.output_txt)