"""
Main Data Cleaner Module

Orchestrates the complete data cleaning pipeline:
1. CSV discovery and validation
2. Data cleaning and normalization
3. Country name standardization
4. SQLite database creation and population
5. Comprehensive reporting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import logging
import time
import json
from datetime import datetime

from .validators import DataValidator
from .normalizers import CountryNormalizer, DataNormalizer
from .database import DatabaseManager

logger = logging.getLogger(__name__)


class DataCleaner:
    """
    Main orchestrator for the data cleaning pipeline.
    
    Coordinates validation, cleaning, normalization, and database operations
    to transform raw CSV files into a standardized SQLite database suitable
    for the country recommendation system.
    """
    
    def __init__(self, country_dict: Dict[str, str], output_db_path: str,
                 winsor_percentiles: Tuple[float, float] = (1.0, 99.0),
                 fuzzy_threshold: int = 90):
        """
        Initialize the data cleaner.
        
        Args:
            country_dict: Standard country names dictionary
            output_db_path: Path for output SQLite database
            winsor_percentiles: Percentiles for winsorization (lower, upper)
            fuzzy_threshold: Minimum fuzzy match score for country names
        """
        self.country_dict = country_dict
        self.output_db_path = output_db_path
        
        # Initialize components
        self.validator = DataValidator()
        self.country_normalizer = CountryNormalizer(country_dict, fuzzy_threshold)
        self.data_normalizer = DataNormalizer(winsor_percentiles[0], winsor_percentiles[1])
        self.db_manager = DatabaseManager(output_db_path)
        
        # Processing configuration
        self.config = {
            'winsor_percentiles': winsor_percentiles,
            'fuzzy_threshold': fuzzy_threshold,
            'missing_value_thresholds': self.validator.missing_thresholds
        }
        
        # Results storage
        self.processing_results = {}
        self.cleaning_report = {}
        
    def _setup_logging(self, log_level: str = 'INFO', log_file: Optional[str] = None):
        """
        Configure logging for the cleaning process.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            log_file: Optional file path for log output
        """
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                *([logging.FileHandler(log_file)] if log_file else [])
            ]
        )
    
    def _load_and_clean_csv(self, file_path: Path, validation_result: Dict) -> Optional[pd.DataFrame]:
        """
        Load and clean a single CSV file.
        
        Args:
            file_path: Path to CSV file
            validation_result: Validation results for the file
            
        Returns:
            Cleaned DataFrame or None if processing failed
        """
        logger.info(f"Processing file: {file_path.name}")
        
        try:
            # Load CSV
            df = pd.read_csv(file_path)
            original_shape = df.shape
            
            # Identify country column
            country_column = validation_result.get('country_column')
            if not country_column:
                # Try to find country column automatically
                potential_country_cols = [col for col in df.columns 
                                        if any(pattern in col.lower() 
                                             for pattern in ['country', 'nation'])]
                if potential_country_cols:
                    country_column = potential_country_cols[0]
                    logger.info(f"Auto-detected country column: {country_column}")
                else:
                    logger.error(f"No country column found in {file_path.name}")
                    return None
            
            # Normalize country names
            df['normalized_country'] = df[country_column].apply(
                self.country_normalizer.normalize_country_name
            )
            
            # Remove rows with unmatched countries
            before_country_filter = len(df)
            df = df[df['normalized_country'].notna()].copy()
            after_country_filter = len(df)
            countries_removed = before_country_filter - after_country_filter
            
            if countries_removed > 0:
                logger.warning(f"Removed {countries_removed} rows with unmatched countries")
            
            # Handle duplicate countries
            if df['normalized_country'].duplicated().any():
                logger.warning(f"Found duplicate countries in {file_path.name}, keeping first occurrence")
                df = df.drop_duplicates(subset=['normalized_country'], keep='first')
            
            # Clean and normalize numeric columns
            numeric_columns = df.select_dtypes(include=[np.number]).columns
            numeric_columns = [col for col in numeric_columns if col != country_column]
            
            cleaning_stats = {}
            
            for column in numeric_columns:
                if column == 'normalized_country':
                    continue
                
                logger.debug(f"Cleaning numeric column: {column}")
                
                # Analyze missing values
                missing_count = df[column].isna().sum()
                missing_rate = missing_count / len(df)
                
                # Apply missing value strategy
                if missing_rate <= self.validator.missing_thresholds['low']:
                    # Use median imputation
                    median_value = df[column].median()
                    df[column] = df[column].fillna(median_value)
                    cleaning_stats[column] = {
                        'missing_strategy': 'median_imputation',
                        'missing_count': missing_count,
                        'missing_rate': missing_rate,
                        'fill_value': median_value
                    }
                elif missing_rate <= self.validator.missing_thresholds['medium']:
                    # Use global median (could be enhanced with regional median)
                    median_value = df[column].median()
                    df[column] = df[column].fillna(median_value)
                    cleaning_stats[column] = {
                        'missing_strategy': 'global_median',
                        'missing_count': missing_count,
                        'missing_rate': missing_rate,
                        'fill_value': median_value
                    }
                else:
                    # Leave as NULL, flag for reporting
                    cleaning_stats[column] = {
                        'missing_strategy': 'leave_null_flagged',
                        'missing_count': missing_count,
                        'missing_rate': missing_rate,
                        'flag': 'high_missing_rate'
                    }
                
                # Normalize the column if it has sufficient data
                if missing_rate < self.validator.missing_thresholds['medium']:
                    normalized_series, norm_stats = self.data_normalizer.normalize_column(
                        df[column], column
                    )
                    df[column] = normalized_series
                    cleaning_stats[column].update(norm_stats)
            
            # Prepare final dataset
            # Keep only normalized country and numeric columns
            final_columns = ['normalized_country'] + [col for col in numeric_columns]
            df_cleaned = df[final_columns].copy()
            df_cleaned = df_cleaned.rename(columns={'normalized_country': 'country'})
            
            # Add filename context for column standardization
            df_cleaned._filename = file_path.stem
            
            # Store processing results
            processing_result = {
                'original_shape': original_shape,
                'final_shape': df_cleaned.shape,
                'countries_removed': countries_removed,
                'numeric_columns_processed': len(numeric_columns),
                'cleaning_statistics': cleaning_stats,
                'file_path': str(file_path)
            }
            
            self.processing_results[file_path.name] = processing_result
            
            logger.info(f"Cleaned {file_path.name}: {original_shape} -> {df_cleaned.shape}")
            
            return df_cleaned
            
        except Exception as e:
            logger.error(f"Failed to clean {file_path.name}: {str(e)}")
            self.processing_results[file_path.name] = {
                'error': str(e),
                'file_path': str(file_path)
            }
            return None
    
    def _merge_datasets(self, cleaned_dataframes: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Merge multiple cleaned datasets into a single comprehensive dataset.
        
        Args:
            cleaned_dataframes: Dictionary of filename -> cleaned DataFrame
            
        Returns:
            Merged DataFrame with all indicators
        """
        logger.info("Merging cleaned datasets")
        
        if not cleaned_dataframes:
            raise ValueError("No cleaned datasets to merge")
        
        # Start with the first dataset
        first_file = list(cleaned_dataframes.keys())[0]
        merged_df = cleaned_dataframes[first_file].copy()
        
        merge_stats = {
            'datasets_merged': 1,
            'initial_countries': len(merged_df),
            'merge_operations': []
        }
        
        # Merge remaining datasets
        for filename, df in list(cleaned_dataframes.items())[1:]:
            before_merge = len(merged_df)
            
            # Preserve filename context before merge
            if hasattr(df, '_filename'):
                df_copy = df.copy()
                df_copy._filename = df._filename
            else:
                df_copy = df.copy()
                df_copy._filename = filename.replace('.csv', '')
            
            # Merge on country column
            merged_df = pd.merge(merged_df, df_copy, on='country', how='outer', suffixes=('', f'_{filename}'))
            
            after_merge = len(merged_df)
            
            merge_stats['merge_operations'].append({
                'filename': filename,
                'countries_before': before_merge,
                'countries_after': after_merge,
                'new_countries': after_merge - before_merge
            })
            
            merge_stats['datasets_merged'] += 1
            
            logger.debug(f"Merged {filename}: {before_merge} -> {after_merge} countries")
        
        # Filter out UNKNOWN countries before finalizing
        before_filter = len(merged_df)
        merged_df = merged_df[~merged_df['country'].str.startswith('UNKNOWN_', na=False)]
        after_filter = len(merged_df)
        
        unknown_countries_removed = before_filter - after_filter
        
        merge_stats['final_countries'] = len(merged_df)
        merge_stats['unknown_countries_removed'] = unknown_countries_removed
        self.cleaning_report['merge_statistics'] = merge_stats
        
        logger.info(f"Merged {merge_stats['datasets_merged']} datasets: {merge_stats['final_countries']} total countries")
        if unknown_countries_removed > 0:
            logger.info(f"Filtered out {unknown_countries_removed} UNKNOWN countries, keeping only successfully matched countries")
        
        return merged_df
    
    def _standardize_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardize column names to match database schema.
        
        Args:
            df: DataFrame with potentially inconsistent column names
            
        Returns:
            DataFrame with standardized column names
        """
        # Define column name mappings with filename context
        filename_to_indicator = {
            'cultural_accessibility': 'cultural_accessibility_score',
            'cultural_accesability': 'cultural_accessibility_score',  # handle typo in folder name
            'tourism_rate': 'tourism_arrivals',
            'tourism': 'tourism_arrivals',
            'natural_spaces': 'natural_spaces_index',
            'natural_rate': 'natural_spaces_index',
            'natural': 'natural_spaces_index'
        }
        
        # Get filename context
        current_filename = getattr(df, '_filename', '').lower()
        
        column_mappings = {
            # Crime and safety
            'crime index': 'crime_index',
            'crime_index': 'crime_index',
            'safety index': 'safety_index',
            'safety_index': 'safety_index',
            
            # English proficiency
            'english_score': 'english_score',
            'english proficiency': 'english_score',
            'english_proficiency': 'english_score',
            
            # Healthcare
            'health_care_index': 'health_care_index',
            'healthcare_index': 'health_care_index',
            'health care index': 'health_care_index',
            'health_care_index': 'health_care_index',
            
            # Cost of living
            'cost_of_living_index': 'cost_of_living_index',
            'cost of living index': 'cost_of_living_index',
            'cost_of_living': 'cost_of_living_index',
            
            # Cultural accessibility - context-aware mapping
            'cultural_accessibility_score': 'cultural_accessibility_score',
            'cultural accessibility score': 'cultural_accessibility_score',
            'cultural_accessibility': 'cultural_accessibility_score',
            'value': 'cultural_accessibility_score' if any(x in current_filename for x in ['cultural', 'accessibility']) else None,
            
            # Public transport
            'public_transport_quality': 'public_transport_quality',
            'public transport quality': 'public_transport_quality',
            'railroad_quality': 'public_transport_quality',
            'public_transport_quality': 'public_transport_quality',
            
            # Tourism - context-aware mapping
            'tourism_arrivals': 'tourism_arrivals',
            'tourism arrivals': 'tourism_arrivals',
            'international_tourism_arrivals': 'tourism_arrivals',
            'value': 'tourism_arrivals' if any(x in current_filename for x in ['tourism', 'arrival']) else 
                    ('cultural_accessibility_score' if any(x in current_filename for x in ['cultural', 'accessibility']) else None),
            
            # Natural spaces - context-aware mapping
            'natural_spaces_index': 'natural_spaces_index',
            'natural spaces index': 'natural_spaces_index',
            'natural_space': 'natural_spaces_index',
            'totalprotectedareakm2': 'natural_spaces_index',
            'total_protected_area_km2': 'natural_spaces_index',
            'totalProtectedAreaKm2': 'natural_spaces_index'
        }
        
        # Normalize column names and apply mappings
        df_renamed = df.copy()
        
        # Create a mapping for current columns
        rename_map = {}
        for col in df.columns:
            if col == 'country':
                continue  # Keep country column as is
            
            col_lower = col.lower().strip()
            mapped_name = None
            
            # Method 1: Exact match
            if col_lower in column_mappings and column_mappings[col_lower] is not None:
                mapped_name = column_mappings[col_lower]
            
            # Method 2: Context-aware mapping for generic names like "value"
            elif col_lower in ['value', 'val'] and hasattr(df, '_filename'):
                filename = df._filename.lower()
                
                # Map based on filename context
                if any(x in filename for x in ['cultural', 'accessibility']):
                    mapped_name = 'cultural_accessibility_score'
                elif any(x in filename for x in ['tourism', 'arrival']):
                    mapped_name = 'tourism_arrivals'
                elif any(x in filename for x in ['natural', 'space', 'protected']):
                    mapped_name = 'natural_spaces_index'
            
            # Method 3: Partial matching for complex names
            elif not mapped_name:
                for pattern, standard_name in column_mappings.items():
                    if pattern and standard_name and (pattern in col_lower or col_lower in pattern):
                        mapped_name = standard_name
                        break
            
            # Method 4: Intelligent mapping for specific patterns
            if not mapped_name:
                if 'totalprotected' in col_lower or 'protected_area' in col_lower:
                    mapped_name = 'natural_spaces_index'
                elif 'health' in col_lower and 'care' in col_lower:
                    mapped_name = 'health_care_index'
                elif 'cost' in col_lower and 'living' in col_lower:
                    mapped_name = 'cost_of_living_index'
            
            # Fallback: clean the original name
            if not mapped_name:
                mapped_name = col_lower.replace(' ', '_').replace('-', '_')
            
            rename_map[col] = mapped_name
        
        if rename_map:
            df_renamed = df_renamed.rename(columns=rename_map)
            logger.info(f"Standardized {len(rename_map)} column names")
        
        return df_renamed
    
    def process_all_files(self, input_folder: str, 
                         log_level: str = 'INFO',
                         log_file: Optional[str] = None,
                         create_backup: bool = True) -> Dict[str, Any]:
        """
        Process all CSV files in the input folder through the complete pipeline.
        
        Args:
            input_folder: Path to folder containing CSV files
            log_level: Logging verbosity level
            log_file: Optional log file path
            create_backup: Whether to create database backup
            
        Returns:
            Dictionary with complete processing results
        """
        start_time = time.time()
        
        # Setup logging
        self._setup_logging(log_level, log_file)
        
        logger.info(f"Starting data cleaning pipeline for: {input_folder}")
        logger.info(f"Output database: {self.output_db_path}")
        
        try:
            # Step 1: Validate all CSV files
            logger.info("Step 1: Validating CSV files")
            validation_results = self.validator.validate_all_files(input_folder)
            
            if validation_results['summary']['failed_validations'] > 0:
                logger.warning(f"Some files failed validation: {validation_results['summary']['failed_validations']}")
            
            # Step 2: Clean individual CSV files
            logger.info("Step 2: Cleaning individual CSV files")
            cleaned_dataframes = {}
            
            for filename, validation_result in validation_results['file_results'].items():
                if validation_result.get('validation_status') == 'success':
                    file_path = Path(validation_result['file_info']['file_path'])
                    cleaned_df = self._load_and_clean_csv(file_path, validation_result)
                    
                    if cleaned_df is not None:
                        cleaned_dataframes[filename] = cleaned_df
            
            if not cleaned_dataframes:
                raise ValueError("No CSV files were successfully cleaned")
            
            # Step 3: Merge datasets
            logger.info("Step 3: Merging datasets")
            merged_df = self._merge_datasets(cleaned_dataframes)
            
            # Step 4: Standardize column names for each dataset individually, then re-merge
            logger.info("Step 4: Standardizing column names")
            
            # Standardize each dataset individually with filename context
            standardized_dataframes = {}
            for filename, df in cleaned_dataframes.items():
                standardized_df = self._standardize_column_names(df)
                standardized_dataframes[filename] = standardized_df
            
            # Re-merge the standardized datasets
            final_df = self._merge_datasets(standardized_dataframes)
            
            # Step 5: Create database and populate
            logger.info("Step 5: Creating and populating database")
            
            # Create database schema
            self.db_manager.create_schema(drop_existing=True)
            
            # Insert complete data into single table with comprehensive imputation
            insertion_stats = self.db_manager.insert_country_indicators_batch(final_df)
            
            # Step 6: Validate database
            logger.info("Step 6: Validating database integrity")
            db_validation = self.db_manager.validate_database_integrity()
            
            # Generate comprehensive report
            processing_time = time.time() - start_time
            
            self.cleaning_report.update({
                'pipeline_config': self.config,
                'processing_time_seconds': processing_time,
                'validation_results': validation_results,
                'processing_results': self.processing_results,
                'country_normalization': self.country_normalizer.get_match_report(),
                'data_normalization': self.data_normalizer.get_normalization_report(),
                'database_insertion': insertion_stats,
                'database_validation': db_validation,
                'final_dataset_shape': final_df.shape,
                'timestamp': datetime.now().isoformat()
            })
            
            logger.info(f"Pipeline completed successfully in {processing_time:.2f} seconds")
            logger.info(f"Final database: {db_validation['total_records']} records, NULL values: {db_validation['null_value_check']['total_nulls']}")
            
            return self.cleaning_report
            
        except Exception as e:
            error_msg = f"Pipeline failed: {str(e)}"
            logger.error(error_msg)
            
            self.cleaning_report.update({
                'pipeline_status': 'failed',
                'error_message': error_msg,
                'processing_time_seconds': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            })
            
            raise
        
        finally:
            # Always close database connection
            self.db_manager.disconnect()
    
    def save_report(self, report_path: str, format: str = 'json'):
        """
        Save the cleaning report to file.
        
        Args:
            report_path: Path for report file
            format: Report format ('json' or 'text')
        """
        if format.lower() == 'json':
            with open(report_path, 'w') as f:
                json.dump(self.cleaning_report, f, indent=2, default=str)
        elif format.lower() == 'text':
            with open(report_path, 'w') as f:
                f.write(self.generate_text_report())
        else:
            raise ValueError(f"Unsupported report format: {format}")
        
        logger.info(f"Report saved to: {report_path}")
    
    def generate_text_report(self) -> str:
        """
        Generate human-readable text report.
        
        Returns:
            Formatted text report
        """
        if not self.cleaning_report:
            return "No cleaning report available"
        
        report = f"""
Data Cleaning Pipeline Report
============================
Generated: {self.cleaning_report.get('timestamp', 'Unknown')}
Processing Time: {self.cleaning_report.get('processing_time_seconds', 0):.2f} seconds

Configuration:
- Winsorization: {self.config['winsor_percentiles']}
- Fuzzy Threshold: {self.config['fuzzy_threshold']}%
- Missing Value Thresholds: {self.config['missing_value_thresholds']}

Validation Summary:
- Files Processed: {self.cleaning_report.get('validation_results', {}).get('summary', {}).get('total_files', 0)}
- Success Rate: {self.cleaning_report.get('validation_results', {}).get('summary', {}).get('success_rate', 0):.1%}

Country Normalization:
- Total Countries: {self.cleaning_report.get('country_normalization', {}).get('total_countries', 0)}
- Match Rate: {self.cleaning_report.get('country_normalization', {}).get('match_rate', 0):.1%}
- Rejections: {self.cleaning_report.get('country_normalization', {}).get('rejections', 0)}

Final Database:
- Countries: {self.cleaning_report.get('database_validation', {}).get('country_count', 0)}
- Indicator Records: {self.cleaning_report.get('database_validation', {}).get('indicator_record_count', 0)}
- Integrity: {self.cleaning_report.get('database_validation', {}).get('integrity_status', 'Unknown')}

Data Completeness:
"""
        
        # Add data completeness information
        db_validation = self.cleaning_report.get('database_validation', {})
        completeness = db_validation.get('data_completeness', {})
        
        for indicator, stats in completeness.items():
            completion_pct = stats.get('completeness_percentage', 0)
            report += f"- {indicator}: {completion_pct}%\n"
        
        return report