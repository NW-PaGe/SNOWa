import glob
import os
import pandas as pd
from datetime import datetime, timedelta
import shutil

def pre_qc():
    """
    Pre-QC Validation for new_runs folder
    Add the new data files to the new_runs folder for the pre-qc step. 
    The new data files will then be added to the runs folder
    """

    print("=== PRE-QC VALIDATION - NEW RUNS ===")
    print("Workflow: new_runs/ → QC validation → runs/ (after approval)")
    print("="*60)

    # Check for files in new_runs folder
    new_runs_path = "new_runs/*.tsv"  # Adjust path as needed
    new_files = glob.glob(new_runs_path)

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
                        sample_ids = row['Sample_ID']
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
                print("   ❌ Reference file 'data/sample_site-counties.csv' not found")
                print("   📋 Unable to check for new sites - showing all sites:")
                for site, count in site_counts.items():
                    print(f"      • {site}: {count} samples")
            except Exception as e:
                print(f"   ❌ Error reading reference file: {e}")
                print("   📋 Unable to check for new sites - showing all sites:")
                for site, count in site_counts.items():
                    print(f"      • {site}: {count} samples")

        # === 5. FLAG DATA QUALITY ISSUES ===
        print("\n5️⃣ DATA QUALITY ISSUES SUMMARY:")

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

        # Duplicates
        if 'Sample_ID' in new_run_df.columns and 'Variant_name' in new_run_df.columns:
            duplicates = new_run_df.duplicated(subset=['Sample_ID', 'Variant_name']).sum()
            if duplicates > 0:
                quality_issues.append(f"Duplicate Sample_ID + Variant combinations ({duplicates} rows)")

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
        print("2. If data looks good, move files to runs/ folder")
        print("3. If issues found, fix source data and re-run QC")

        move_files = input(f"\nMove {len(new_files)} file(s) to runs/ folder? (y/n): ").lower().strip()

        if move_files == 'y':
            print(f"\n🚀 Moving files to runs/ folder...")

            # Create runs folder if it doesn't exist
            os.makedirs('runs', exist_ok=True)

            moved_count = 0
            for file in new_files:
                try:
                    filename = os.path.basename(file)
                    destination = os.path.join('runs', filename)
                    shutil.move(file, destination)
                    print(f"   ✅ Moved: {filename}")
                    moved_count += 1
                except Exception as e:
                    print(f"   ❌ Failed to move {filename}: {e}")

            print(f"\n🎉 Successfully moved {moved_count}/{len(new_files)} files to runs/ folder")
            print("   Ready for main data processing!")
        else:
            print(f"\n📋 Files remain in new_runs/ folder for further review")
            print("   Re-run this QC script after addressing any issues")

# Run the Pre-QC validation
pre_qc()