import glob
import os
import pandas as pd
from datetime import datetime, timedelta
import shutil
import argparse

def pre_qc(directory): ## I added directory here - that will come from args.parse (see end of this script)
    """
    Pre-QC Validation for new_runs folder
    Add the new data files to the new_runs folder for the pre-qc step. 
    The new data files will then be added to the runs folder
    """

    # Check for files in new_runs folder
    new_runs_path = os.path.join(directory, "*.tsv")
    new_files = glob.glob(new_runs_path)

    print("=== PRE-QC VALIDATION - NEW RUNS ===")
    print("Workflow: new_runs/ → QC validation → runs/ (after approval)")
    print("="*60)

    if not new_files:
        print("📂 No TSV files found in new_runs/ folder - skipping Pre-QC validation")
        print("   To run Pre-QC, place new sequencing files in the new_runs/ directory")
        print("   Continuing with notebook execution...")
    else:
        print(f"📁 Found {len(new_files)} file(s) in new_runs/ folder:")

        for file in new_files:
            file_size = os.path.getsize(file) / 1024  # KB
            mod_time = datetime.fromtimestamp(os.path.getmtime(file))
            print(f"   • {os.path.basename(file)} ({file_size:.1f} KB, modified: {mod_time.strftime('%Y-%m-%d %H:%M')})")

        # Load all new files
        print(f"\n🔄 Loading {len(new_files)} file(s)...")
        try:
            dataframes = []
            for file in new_files:
                # Determine if CSV or TSV and read accordingly
                if file.endswith('.tsv'):
                    df = pd.read_csv(file, sep='\t')
                else:
                    df = pd.read_csv(file)
                dataframes.append(df)

            new_run_df = pd.concat(dataframes, ignore_index=True)
            print(f"✅ Successfully loaded {len(new_run_df)} total rows")
        except Exception as e:
            print(f"❌ Error loading files: {e}")
            return

        print("\n" + "="*60)
        print("COMPREHENSIVE PRE-QC VALIDATION")
        print("="*60)

        # === 1. CHECK FOR MISSING DATA POINTS ===
        print("\n1️⃣ MISSING DATA CHECK:")
        critical_columns = ['Lab_ID', 'Sample_ID', 'Sample_Site', 'Sample_Collection_Date', 
                           'Variant_name', 'Variant_proportion']

        missing_data_issues = False
        for col in critical_columns:
            if col in new_run_df.columns:
                missing_count = new_run_df[col].isnull().sum()
                missing_percent = (missing_count / len(new_run_df)) * 100
                status = "⚠️" if missing_count > 0 else "✅"
                print(f"   {status} {col}: {missing_count} missing ({missing_percent:.1f}%)")
                if missing_count > 0:
                    missing_data_issues = True
            else:
                print(f"   ❌ {col}: Column not found in data")
                missing_data_issues = True

        # === 2. VALIDATE SAMPLE DATES ===
        print("\n2️⃣ SAMPLE DATE VALIDATION:")
        current_date = datetime.now()
        one_month_ago = current_date - timedelta(days=30)
        one_month_future = current_date + timedelta(days=30)

        if 'Sample_Collection_Date' in new_run_df.columns:
            try:
                dates = pd.to_datetime(new_run_df['Sample_Collection_Date'], errors='coerce')

                # Check for invalid date formats
                invalid_dates = dates.isnull().sum()
                if invalid_dates > 0:
                    print(f"   ⚠️ {invalid_dates} rows have invalid date formats")
                else:
                    print(f"   ✅ All dates have valid formats")

                valid_dates = dates.dropna()
                if len(valid_dates) > 0:
                    print(f"   📅 Date range: {valid_dates.min().date()} to {valid_dates.max().date()}")

                    # Check if dates are within one month of current date
                    within_range = ((valid_dates >= one_month_ago) & (valid_dates <= one_month_future)).sum()
                    total_dates = len(valid_dates)
                    print(f"   📊 Dates within ±1 month of today: {within_range}/{total_dates} ({within_range/total_dates*100:.1f}%)")

                    if within_range < total_dates:
                        outside_range = total_dates - within_range
                        print(f"   ⚠️ {outside_range} dates are outside the expected ±1 month range")

            except Exception as e:
                print(f"   ❌ Error processing dates: {e}")
        else:
            print("   ❌ Sample_Collection_Date column not found")

        # === 3. IDENTIFY INCORRECT TEMPORAL ENTRIES ===
        print("\n3️⃣ TEMPORAL ENTRY VALIDATION:")
        if 'Sample_Collection_Date' in new_run_df.columns and len(valid_dates) > 0:

            # Print all unique dates for manual inspection
            print("   📋 ALL UNIQUE DATES (for manual review):")
            unique_dates = valid_dates.drop_duplicates().sort_values()

            for date in unique_dates:
                date_mask = (dates == date)
                count = date_mask.sum()

                # Flag suspicious dates
                flag = ""
                if date.year < 2024:
                    flag = "🔴 WRONG YEAR"
                elif date.year == 2024 and current_date.year == 2025:
                    flag = "🟡 SUSPICIOUS (2024 in new data?)"
                elif date > one_month_future:
                    flag = "🟠 FUTURE DATE"
                elif date < one_month_ago:
                    flag = "🟡 OLD DATE"

                print(f"      {date.strftime('%Y-%m-%d (%A)')}: {count} samples {flag}")

                # Break down by site for this date
                if 'Sample_Site' in new_run_df.columns and 'Sample_ID' in new_run_df.columns:
                    date_data = new_run_df[date_mask]
                    site_breakdown = date_data.groupby('Sample_Site').agg({
                        'Sample_ID': lambda x: list(x.unique())
                    })

                    for site, row in site_breakdown.iterrows():
                        sample_ids_num = row['Sample_ID']
                        sample_ids = [str(x) for x in sample_ids_num]
                        site_count = len(sample_ids)
                        print(f"         • {site}: {site_count} samples (Sample_IDs: {sample_ids})")
                    print()  # Add blank line between dates

            # Summary by year and month
            print(f"\n   📊 SUMMARY BY TIME PERIOD:")
            year_counts = valid_dates.dt.year.value_counts().sort_index()
            for year, count in year_counts.items():
                flag = "🔴" if year < 2024 else "🟡" if year == 2024 else "✅"
                print(f"      {flag} {year}: {count} samples")

            month_counts = valid_dates.dt.to_period('M').value_counts().sort_index()
            print(f"   📅 BY MONTH:")
            for month, count in month_counts.items():
                print(f"      {month}: {count} samples")

        # === 4. SCREEN FOR NEW SAMPLE COLLECTION SITES ===
        print("\n4️⃣ SAMPLE COLLECTION SITES:")
        if 'Sample_Site' in new_run_df.columns:
            site_counts = new_run_df['Sample_Site'].value_counts()
            total_sites = len(site_counts)
            print(f"   📍 Total unique sample sites in new data: {total_sites}")

            # Load reference sample sites file
            try:
                reference_sites_df = pd.read_csv('defaults/sample_site-counties.csv')
                # Get known sample sites (assuming the site names are in a column)
                # Adjust column name as needed - could be 'Sample_Site', 'Site', 'site_name', etc.
                site_column = None
                for col in ['Sample_Site', 'Site', 'site_name', 'WWTP', 'Site_Name']:
                    if col in reference_sites_df.columns:
                        site_column = col
                        break

                if site_column:
                    known_sites = set(reference_sites_df[site_column].dropna().str.strip())
                    new_data_sites = set(new_run_df['Sample_Site'].dropna().str.strip())

                    # Find truly new sites
                    new_sites = new_data_sites - known_sites
                    known_sites_in_data = new_data_sites & known_sites

                    print(f"   📋 Reference file loaded: {len(known_sites)} known sites")
                    print(f"   ✅ Known sites in new data: {len(known_sites_in_data)}")

                    if new_sites:
                        print(f"   🔍 NEW SITES DETECTED ({len(new_sites)} sites):")
                        for site in sorted(new_sites):
                            count = site_counts.get(site, 0)
                            print(f"      • {site}: {count} samples")
                        print(f"   ⚠️  ACTION REQUIRED: Review new sites and update reference file if valid")
                    else:
                        print("   ✅ No new sample sites detected")

                    # Show all sites with status
                    print(f"\n   📋 ALL SAMPLE SITES IN NEW DATA:")
                    for site, count in site_counts.items():
                        status = "🆕 NEW" if site.strip() in new_sites else "✅ KNOWN"
                        print(f"      • {site}: {count} samples ({status})")

                else:
                    print("   ❌ Could not identify sample site column in reference file")
                    print(f"   Available columns: {list(reference_sites_df.columns)}")
                    # Fallback to original logic
                    print(f"   📋 ALL SAMPLE SITES (unable to check against reference):")
                    for site, count in site_counts.items():
                        print(f"      • {site}: {count} samples")

            except FileNotFoundError:
                print("   ❌ Reference file 'defaults/sample_site-counties.csv' not found")
                print("   📋 Unable to check for new sites - showing all sites:")
                for site, count in site_counts.items():
                    print(f"      • {site}: {count} samples")
            except Exception as e:
                print(f"   ❌ Error reading reference file: {e}")
                print("   📋 Unable to check for new sites - showing all sites:")
                for site, count in site_counts.items():
                    print(f"      • {site}: {count} samples")

        # === 5. CHECK FOR NEW VARIANTS ===
        print("\n5️⃣ VARIANT COMPARISON:")
        if 'Variant_name' in new_run_df.columns:
            # Get all unique variants from new data
            new_variants_set = set(new_run_df['Variant_name'].dropna().unique())
            total_new_variants = len(new_variants_set)
            print(f"   🧬 Total unique variants in new data: {total_new_variants}")

            # Try to load variant reference file
            try:
                variant_ref_df = pd.read_csv('results/qc/variant_reference.csv')
                print(f"   📋 Variant reference file loaded: {len(variant_ref_df)} known variants")

                # Get known variants from reference
                if 'Variant_name' in variant_ref_df.columns:
                    known_variants_set = set(variant_ref_df['Variant_name'].dropna().unique())

                    # Find new variants
                    truly_new_variants = new_variants_set - known_variants_set
                    known_variants_in_data = new_variants_set & known_variants_set

                    print(f"   ✅ Known variants in new data: {len(known_variants_in_data)}")

                    if truly_new_variants:
                        print(f"\n   🆕 NEW VARIANTS DETECTED ({len(truly_new_variants)} variants):")

                        # Create detailed report for new variants
                        new_variant_details = []

                        for variant in sorted(truly_new_variants):
                            # Get all occurrences of this variant
                            variant_data = new_run_df[new_run_df['Variant_name'] == variant]

                            # Get unique dates where this variant appears
                            if 'Sample_Collection_Date' in variant_data.columns:
                                variant_dates = pd.to_datetime(variant_data['Sample_Collection_Date'], errors='coerce').dropna()
                                unique_dates = sorted(variant_dates.dt.date.unique())
                                date_range = f"{unique_dates[0]} to {unique_dates[-1]}" if len(unique_dates) > 1 else str(unique_dates[0])
                            else:
                                date_range = "N/A"
                                unique_dates = []

                            # Get sample sites where this variant appears
                            if 'Sample_Site' in variant_data.columns:
                                sites = variant_data['Sample_Site'].dropna().unique()
                                sites_str = ", ".join(sorted(sites))
                            else:
                                sites = []
                                sites_str = "N/A"

                            # Count occurrences
                            occurrence_count = len(variant_data)

                            # Print to console
                            print(f"      • {variant}")
                            print(f"         - First detected: {unique_dates[0] if unique_dates else 'N/A'}")
                            print(f"         - Date range: {date_range}")
                            print(f"         - Sample sites: {sites_str}")
                            print(f"         - Total occurrences: {occurrence_count}")

                            # Store for CSV export
                            new_variant_details.append({
                                'Variant_name': variant,
                                'First_detected': unique_dates[0] if unique_dates else None,
                                'Last_detected': unique_dates[-1] if len(unique_dates) > 1 else (unique_dates[0] if unique_dates else None),
                                'Date_range': date_range,
                                'Sample_sites': sites_str,
                                'Total_occurrences': occurrence_count,
                                'Detection_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            })

                        # Save new variants to CSV file
                        new_variants_df = pd.DataFrame(new_variant_details)
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        output_filename = f'results/new_variants_detected_{timestamp}.csv'
                        new_variants_df.to_csv(output_filename, index=False)
                        print(f"\n   💾 New variants report saved to: {output_filename}")
                        print(f"   ⚠️  ACTION REQUIRED: Review new variants; results/qc/variant_reference.csv will automatically update")

                    else:
                        print("   ✅ No new variants detected - all variants in new data are in reference file")

                    # Show summary of all variants
                    print(f"\n   📊 VARIANT SUMMARY:")
                    print(f"      • Known variants: {len(known_variants_in_data)}")
                    print(f"      • New variants: {len(truly_new_variants)}")
                    print(f"      • Total variants in new data: {total_new_variants}")

                else:
                    print("   ❌ 'Variant_name' column not found in variant reference file")
                    print("   📋 Unable to compare variants - showing all variants in new data:")
                    variant_counts = new_run_df['Variant_name'].value_counts()
                    for variant, count in variant_counts.items():
                        print(f"      • {variant}: {count} occurrences")

            except FileNotFoundError:
                print("   ⚠️ Variant reference file 'variant_reference.csv' not found")
                print("   📋 Unable to check for new variants - showing all variants in new data:")
                variant_counts = new_run_df['Variant_name'].value_counts()
                for variant, count in variant_counts.head(20).items():  # Show top 20
                    print(f"      • {variant}: {count} occurrences")
                if len(variant_counts) > 20:
                    print(f"      ... and {len(variant_counts) - 20} more variants")
                print("\n   💡 TIP: Create variant_reference.csv to enable new variant detection")

            except Exception as e:
                print(f"   ❌ Error reading variant reference file: {e}")
                print("   📋 Unable to check for new variants")

        else:
            print("   ❌ 'Variant_name' column not found in new data")

        # === 6. FLAG DATA QUALITY ISSUES ===
        print("\n6️⃣ DATA QUALITY ISSUES SUMMARY:")

        quality_issues = []

        # Missing data issues
        if missing_data_issues:
            quality_issues.append("Missing data in critical columns")

        # Date issues
        if 'Sample_Collection_Date' in new_run_df.columns and len(valid_dates) > 0:
            old_dates = (valid_dates < pd.Timestamp('2024-01-01')).sum()
            future_dates = (valid_dates > one_month_future).sum()
            if old_dates > 0:
                quality_issues.append(f"Dates before 2024 ({old_dates} samples)")
            if future_dates > 0:
                quality_issues.append(f"Future dates beyond expected range ({future_dates} samples)")

        # Variant proportion issues
        if 'Variant_proportion' in new_run_df.columns:
            prop_col = pd.to_numeric(new_run_df['Variant_proportion'], errors='coerce')
            negative_props = (prop_col < 0).sum()
            over_one_props = (prop_col > 1).sum()
            if negative_props > 0:
                quality_issues.append(f"Negative variant proportions ({negative_props} values)")
            if over_one_props > 0:
                quality_issues.append(f"Variant proportions >1.0 ({over_one_props} values)")

        # Duplicates - Check for same Sample_ID with different collection dates
        if 'Sample_ID' in new_run_df.columns and 'Sample_Collection_Date' in new_run_df.columns:
            # Group by Sample_ID and check if there are multiple unique collection dates
            sample_date_check = new_run_df.groupby('Sample_ID')['Sample_Collection_Date'].nunique()
            problematic_samples = sample_date_check[sample_date_check > 1]

            if len(problematic_samples) > 0:
                # Get the columns to display
                cols_to_show = ['Sample_ID', 'Sample_Collection_Date']
                if 'Lab_ID' in new_run_df.columns:
                    cols_to_show.append('Lab_ID')
                if 'Sample_Site' in new_run_df.columns:
                    cols_to_show.append('Sample_Site')

                # Get unique combinations for problematic samples
                duplicate_rows = new_run_df[new_run_df['Sample_ID'].isin(problematic_samples.index)][cols_to_show].drop_duplicates()

                # Format as a readable list
                duplicate_list = "\n      • ".join([
                    f"Sample_ID: {row['Sample_ID']}, Collection_Date: {row['Sample_Collection_Date']}, Lab_ID: {row.get('Lab_ID', 'N/A')}, Sample_Site: {row.get('Sample_Site', 'N/A')}"
                    for _, row in duplicate_rows.iterrows()
                ])

                quality_issues.append(f"Sample_IDs with different collection dates found ({len(problematic_samples)} samples affected):\n      • {duplicate_list}")

        # Summary
        if quality_issues:
            print("   ⚠️ ISSUES FOUND:")
            for issue in quality_issues:
                print(f"      • {issue}")
            print(f"\n   🔍 RECOMMENDATION: Review flagged issues before proceeding")
        else:
            print("   ✅ NO MAJOR QUALITY ISSUES DETECTED")

        print("\n" + "="*60)
        print("PRE-QC VALIDATION COMPLETE")
        print("="*60)

        # Optional: Move files after review
        print(f"\n🎯 NEXT STEPS:")
        print("1. Review all flagged issues above")
        print("2. If new variants detected, review the saved CSV report")
        print("3. If data looks good, move files to runs/ folder")
        print("4. If issues found, fix source data and re-run QC")

    if quality_issues:
        print("\n❌ PRE-QC FAILED")
        print("Data needs review due to failed QC checks.")
        print("Review and correct the data, then rerun the pipeline.")
        print("The new file will remain in new_runs/ and will not be included in the analysis.")

    else:
        print("\n✅ PRE-QC PASSED")
        print("Moving approved file(s) to runs/ for inclusion in the analysis.")

        os.makedirs("runs", exist_ok=True)

        for file in new_files:
            filename = os.path.basename(file)
            destination = os.path.join("runs", filename)
            shutil.move(file, destination)
            print(f"   ✅ Moved: {filename}")


# Run the Pre-QC validation
if __name__ == "__main__":
    ## pull in the parameter that's used with the flag in line 23 of the snakefile.
    ## there's an example of this from lines 4-12 of check_variant_lineage_mapping.py
    ## That you can probably copy/paste from.
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory")
    args = parser.parse_args()
    directory = args.directory # you can make a string object from args after parsing
    pre_qc(directory) # This is just coming from the line above. you could pass args.flag directory but this is maybe more readable