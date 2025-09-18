"""
Data Validation Module

Handles:
1. CSV file structure validation
2. Data quality assessment
3. Missing value analysis
4. Schema compliance checking
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Comprehensive data validation for country indicator datasets.
    
    Performs structure validation, quality assessment, and missing value analysis
    with detailed reporting for cleaning pipeline decisions.
    """
    
    def __init__(self):
        """Initialize data validator with quality thresholds."""
        # Missing value thresholds for different imputation strategies
        self.missing_thresholds = {
            'low': 0.10,    # ≤10%: median imputation
            'medium': 0.40   # 10-40%: regional/global median, >40%: leave NULL
        }
        
        # Expected column patterns for automatic indicator detection
        self.indicator_patterns = {
            'country': ['country', 'country_name', 'nation'],
            'crime': ['crime', 'safety'],
            'english': ['english', 'proficiency'],
            'health': ['health', 'care', 'medical'],
            'cost': ['cost', 'living', 'expense'],
            'cultural': ['cultural', 'accessibility', 'access'],
            'transport': ['transport', 'transportation', 'railroad', 'public'],
            'tourism': ['tourism', 'arrival', 'visitor'],
            'natural': ['natural', 'space', 'environment']
        }
        
        # Validation results storage
        self.validation_results = {}
    
    def discover_csv_files(self, input_folder: str) -> List[Path]:
        """
        Discover and validate CSV files in input folder.
        
        Args:
            input_folder: Path to folder containing CSV files
            
        Returns:
            List of valid CSV file paths
            
        Raises:
            FileNotFoundError: If input folder doesn't exist
            ValueError: If no CSV files found
        """
        folder_path = Path(input_folder)
        
        # Check if folder exists
        if not folder_path.exists():
            raise FileNotFoundError(f"Input folder not found: {input_folder}")
        
        if not folder_path.is_dir():
            raise ValueError(f"Path is not a directory: {input_folder}")
        
        # Find CSV files recursively
        csv_files = list(folder_path.rglob("*.csv"))
        
        if not csv_files:
            raise ValueError(f"No CSV files found in: {input_folder}")
        
        logger.info(f"Discovered {len(csv_files)} CSV files")
        return csv_files
    
    def _detect_indicator_type(self, columns: List[str], filename: str) -> Optional[str]:
        """
        Detect the type of indicator based on column names and filename.
        
        Args:
            columns: List of column names
            filename: Name of the CSV file
            
        Returns:
            Detected indicator type or None
        """
        # Combine column names and filename for pattern matching
        text_to_search = ' '.join(columns + [filename]).lower()
        
        # Check each indicator pattern
        for indicator_type, patterns in self.indicator_patterns.items():
            if indicator_type == 'country':
                continue  # Skip country column detection
            
            # Count pattern matches
            matches = sum(1 for pattern in patterns if pattern in text_to_search)
            if matches > 0:
                logger.debug(f"Detected {indicator_type} indicator in {filename}")
                return indicator_type
        
        logger.warning(f"Could not detect indicator type for {filename}")
        return None
    
    def _analyze_missing_values(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze missing values and determine imputation strategy.
        
        Args:
            df: DataFrame to analyze
            
        Returns:
            Dictionary with missing value analysis
        """
        analysis = {}
        
        for column in df.columns:
            if df[column].dtype in ['object', 'string']:
                continue  # Skip non-numeric columns for missing analysis
            
            total_count = len(df)
            missing_count = df[column].isna().sum()
            missing_rate = missing_count / total_count if total_count > 0 else 0
            
            # Determine imputation strategy based on missing rate
            if missing_rate <= self.missing_thresholds['low']:
                strategy = 'median_imputation'
            elif missing_rate <= self.missing_thresholds['medium']:
                strategy = 'regional_or_global_median'
            else:
                strategy = 'leave_null_and_flag'
            
            analysis[column] = {
                'missing_count': missing_count,
                'missing_rate': missing_rate,
                'imputation_strategy': strategy,
                'data_type': str(df[column].dtype),
                'non_null_count': total_count - missing_count
            }
        
        return analysis
    
    def _validate_numeric_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate numeric columns for outliers and data quality.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            Dictionary with numeric validation results
        """
        numeric_analysis = {}
        
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for column in numeric_columns:
            series = df[column].dropna()
            
            if len(series) == 0:
                numeric_analysis[column] = {'error': 'No valid numeric data'}
                continue
            
            # Basic statistics
            stats = {
                'min': series.min(),
                'max': series.max(),
                'mean': series.mean(),
                'median': series.median(),
                'std': series.std(),
                'q25': series.quantile(0.25),
                'q75': series.quantile(0.75)
            }
            
            # Outlier detection using IQR method
            iqr = stats['q75'] - stats['q25']
            lower_bound = stats['q25'] - 1.5 * iqr
            upper_bound = stats['q75'] + 1.5 * iqr
            
            outliers_lower = (series < lower_bound).sum()
            outliers_upper = (series > upper_bound).sum()
            total_outliers = outliers_lower + outliers_upper
            
            # Check for negative values (might be unexpected for some indicators)
            negative_count = (series < 0).sum()
            
            # Zero values (might indicate missing data coded as 0)
            zero_count = (series == 0).sum()
            
            numeric_analysis[column] = {
                **stats,
                'outliers_lower': outliers_lower,
                'outliers_upper': outliers_upper,
                'total_outliers': total_outliers,
                'outlier_rate': total_outliers / len(series),
                'negative_values': negative_count,
                'zero_values': zero_count,
                'iqr_lower_bound': lower_bound,
                'iqr_upper_bound': upper_bound
            }
        
        return numeric_analysis
    
    def validate_csv_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Comprehensive validation of a single CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            Dictionary with complete validation results
        """
        logger.info(f"Validating CSV file: {file_path.name}")
        
        try:
            # Load CSV file
            df = pd.read_csv(file_path)
            
            # Basic file information
            file_info = {
                'filename': file_path.name,
                'file_path': str(file_path),
                'file_size_mb': file_path.stat().st_size / (1024 * 1024),
                'row_count': len(df),
                'column_count': len(df.columns),
                'columns': list(df.columns)
            }
            
            # Detect indicator type
            indicator_type = self._detect_indicator_type(df.columns.tolist(), file_path.stem)
            
            # Find country column
            country_column = None
            for col in df.columns:
                if any(pattern in col.lower() for pattern in self.indicator_patterns['country']):
                    country_column = col
                    break
            
            # Analyze missing values
            missing_analysis = self._analyze_missing_values(df)
            
            # Validate numeric data
            numeric_analysis = self._validate_numeric_data(df)
            
            # Check for duplicate countries
            duplicates = {}
            if country_column:
                duplicate_countries = df[country_column].duplicated().sum()
                if duplicate_countries > 0:
                    duplicate_values = df[df[country_column].duplicated(keep=False)][country_column].tolist()
                    duplicates = {
                        'count': duplicate_countries,
                        'values': duplicate_values
                    }
            
            # Compile validation results
            validation_result = {
                'file_info': file_info,
                'indicator_type': indicator_type,
                'country_column': country_column,
                'missing_analysis': missing_analysis,
                'numeric_analysis': numeric_analysis,
                'duplicates': duplicates,
                'validation_status': 'success',
                'warnings': [],
                'errors': []
            }
            
            # Add warnings based on analysis
            if not country_column:
                validation_result['warnings'].append("No country column detected")
            
            if not indicator_type:
                validation_result['warnings'].append("Could not detect indicator type")
            
            # Check for high missing rates
            high_missing_cols = [col for col, analysis in missing_analysis.items() 
                               if analysis.get('missing_rate', 0) > self.missing_thresholds['medium']]
            if high_missing_cols:
                validation_result['warnings'].append(f"High missing rates in columns: {high_missing_cols}")
            
            # Check for duplicate countries
            if duplicates.get('count', 0) > 0:
                validation_result['warnings'].append(f"Found {duplicates['count']} duplicate countries")
            
            # Store results for reporting
            self.validation_results[file_path.name] = validation_result
            
            return validation_result
            
        except Exception as e:
            error_result = {
                'file_info': {'filename': file_path.name, 'file_path': str(file_path)},
                'validation_status': 'error',
                'error_message': str(e),
                'errors': [f"Failed to load CSV: {str(e)}"]
            }
            
            self.validation_results[file_path.name] = error_result
            logger.error(f"Validation failed for {file_path.name}: {str(e)}")
            
            return error_result
    
    def validate_all_files(self, input_folder: str) -> Dict[str, Any]:
        """
        Validate all CSV files in the input folder.
        
        Args:
            input_folder: Path to folder containing CSV files
            
        Returns:
            Dictionary with validation results for all files
        """
        logger.info(f"Starting validation of all CSV files in: {input_folder}")
        
        # Discover CSV files
        csv_files = self.discover_csv_files(input_folder)
        
        # Validate each file
        for file_path in csv_files:
            self.validate_csv_file(file_path)
        
        # Generate summary report
        summary = self._generate_validation_summary()
        
        return {
            'summary': summary,
            'file_results': self.validation_results
        }
    
    def _generate_validation_summary(self) -> Dict[str, Any]:
        """
        Generate summary of validation results across all files.
        
        Returns:
            Dictionary with validation summary
        """
        total_files = len(self.validation_results)
        successful_files = sum(1 for result in self.validation_results.values() 
                              if result.get('validation_status') == 'success')
        failed_files = total_files - successful_files
        
        # Aggregate statistics
        total_rows = sum(result.get('file_info', {}).get('row_count', 0) 
                        for result in self.validation_results.values())
        
        total_countries = 0
        detected_indicators = set()
        total_warnings = 0
        
        for result in self.validation_results.values():
            if result.get('validation_status') == 'success':
                total_countries += result.get('file_info', {}).get('row_count', 0)
                if result.get('indicator_type'):
                    detected_indicators.add(result['indicator_type'])
                total_warnings += len(result.get('warnings', []))
        
        return {
            'total_files': total_files,
            'successful_validations': successful_files,
            'failed_validations': failed_files,
            'success_rate': successful_files / total_files if total_files > 0 else 0,
            'total_data_rows': total_rows,
            'estimated_countries': total_countries,
            'detected_indicators': list(detected_indicators),
            'total_warnings': total_warnings,
            'missing_value_thresholds': self.missing_thresholds
        }