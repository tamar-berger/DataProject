#!/usr/bin/env python3
"""
Script to run the data cleaner with standardized CSV files.
"""

import sys
import os
from pathlib import Path
import pandas as pd

# Add current directory to Python path
sys.path.insert(0, os.getcwd())

from data_cleaner.cleaner import DataCleaner

def get_all_standardized_countries():
    """Extract all unique country names from standardized CSV files."""
    countries = set()
    csv_folder = Path("pre_process")
    
    for csv_file in csv_folder.rglob("*.csv"):
        try:
            df = pd.read_csv(csv_file)
            # Look for country column (should be standardized as 'country')
            if 'country' in df.columns:
                country_names = df['country'].dropna().astype(str).str.strip()
                countries.update(country_names)
        except Exception as e:
            print(f"Warning: Could not read {csv_file}: {e}")
    
    # Remove empty strings
    countries = {name for name in countries if name and name.strip()}
    print(f"Found {len(countries)} unique standardized countries")
    
    # Create identity mapping (since names are already standardized)
    return {country: country for country in countries}

def main():
    """Main entry point for running the data cleaner."""
    
    # Configuration
    input_folder = "pre_process"
    output_db = "country_rates.db"
    
    # Remove existing database if it exists
    if os.path.exists(output_db):
        os.remove(output_db)
        print(f"Removed existing database: {output_db}")
    
    # Get standardized country dictionary
    country_dict = get_all_standardized_countries()
    print(f"Using {len(country_dict)} countries in dictionary")
    
    # Create data cleaner instance
    cleaner = DataCleaner(
        country_dict=country_dict,
        output_db_path=output_db,
        winsor_percentiles=(1.0, 99.0),
        fuzzy_threshold=90  # High threshold since names are standardized
    )
    
    print(f"Starting data cleaning pipeline...")
    print(f"Input folder: {input_folder}")
    print(f"Output database: {output_db}")
    
    try:
        # Process all files
        results = cleaner.process_all_files(
            input_folder=input_folder,
            log_level='INFO'
        )
        
        print(f"\n✅ Data cleaning completed successfully!")
        print(f"Database created: {output_db}")
        
        # Save detailed report
        report_path = f"cleaning_report_{Path(output_db).stem}.json"
        cleaner.save_report(report_path, format='json')
        print(f"Detailed report saved: {report_path}")
        
        # Print summary
        if 'database_validation' in results:
            db_stats = results['database_validation']
            print(f"\nDatabase Summary:")
            print(f"- Total countries: {db_stats.get('country_count', 'Unknown')}")
            print(f"- Total records: {db_stats.get('total_records', 'Unknown')}")
            print(f"- NULL values: {db_stats.get('null_value_check', {}).get('total_nulls', 'Unknown')}")
        
        return results
        
    except Exception as e:
        print(f"❌ Error during data cleaning: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    main()