"""
Data Validation and Quality Assessment Module
Validates data integrity, consistency, and quality for the recommendation system
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
from datetime import datetime
import warnings

logger = logging.getLogger(__name__)


class DataValidator:
    """
    Comprehensive data validation and quality assessment for country recommendation data.
    
    Validates:
    - Data schema and types
    - Value ranges and constraints
    - Data consistency and relationships
    - Feature quality and completeness
    - Business logic constraints
    """
    
    def __init__(self, 
                 strict_mode: bool = False,
                 auto_fix: bool = True):
        """
        Initialize data validator
        
        Args:
            strict_mode: Whether to be strict about validation failures
            auto_fix: Whether to attempt automatic fixes for common issues
        """
        self.strict_mode = strict_mode
        self.auto_fix = auto_fix
        
        # Define expected data schema
        self.expected_schema = {
            'country_name': {'type': 'string', 'required': True, 'unique': True},
            'safety_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'crime_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'english_score_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'health_care_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'cost_of_living_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'public_transport_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'cultural_accessibility_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'natural_spaces_rate': {'type': 'numeric', 'range': (0, 1), 'required': False},
            'tourism_arrivals_rate': {'type': 'numeric', 'range': (0, 1), 'required': False}
        }
        
        # Business logic constraints
        self.business_rules = [
            {
                'name': 'safety_crime_inverse',
                'description': 'Safety and crime rates should be inversely related',
                'validator': self._validate_safety_crime_relationship
            },
            {
                'name': 'feature_completeness',
                'description': 'Countries should have reasonable feature coverage',
                'validator': self._validate_feature_completeness
            },
            {
                'name': 'value_consistency',
                'description': 'Related features should be internally consistent',
                'validator': self._validate_value_consistency
            }
        ]
    
    def validate_data(self, 
                     countries_df: pd.DataFrame,
                     return_fixes: bool = True) -> Tuple[bool, Dict[str, Any], Optional[pd.DataFrame]]:
        """
        Comprehensive data validation
        
        Args:
            countries_df: Input data to validate
            return_fixes: Whether to return automatically fixed data
            
        Returns:
            Tuple of (is_valid, validation_report, fixed_dataframe)
        """
        logger.info("Starting comprehensive data validation")
        
        validation_report = {
            'timestamp': datetime.now().isoformat(),
            'original_shape': countries_df.shape,
            'validation_results': {},
            'errors': [],
            'warnings': [],
            'fixes_applied': [],
            'overall_status': 'unknown'
        }
        
        fixed_df = countries_df.copy() if self.auto_fix else None
        
        # Step 1: Schema validation
        schema_valid, schema_report = self._validate_schema(countries_df)
        validation_report['validation_results']['schema'] = schema_report
        
        if not schema_valid and self.strict_mode:
            validation_report['overall_status'] = 'failed'
            return False, validation_report, fixed_df
        
        # Step 2: Data type validation
        types_valid, types_report, type_fixes = self._validate_data_types(countries_df)
        validation_report['validation_results']['data_types'] = types_report
        
        if self.auto_fix and type_fixes and fixed_df is not None:
            fixed_df = self._apply_type_fixes(fixed_df, type_fixes)
            validation_report['fixes_applied'].extend(type_fixes)
        
        # Step 3: Value range validation
        ranges_valid, ranges_report, range_fixes = self._validate_value_ranges(
            fixed_df if fixed_df is not None else countries_df
        )
        validation_report['validation_results']['value_ranges'] = ranges_report
        
        if self.auto_fix and range_fixes and fixed_df is not None:
            fixed_df = self._apply_range_fixes(fixed_df, range_fixes)
            validation_report['fixes_applied'].extend(range_fixes)
        
        # Step 4: Data consistency validation
        consistency_valid, consistency_report = self._validate_data_consistency(
            fixed_df if fixed_df is not None else countries_df
        )
        validation_report['validation_results']['consistency'] = consistency_report
        
        # Step 5: Business rules validation
        business_valid, business_report = self._validate_business_rules(
            fixed_df if fixed_df is not None else countries_df
        )
        validation_report['validation_results']['business_rules'] = business_report
        
        # Step 6: Feature quality assessment
        quality_report = self._assess_feature_quality(
            fixed_df if fixed_df is not None else countries_df
        )
        validation_report['validation_results']['feature_quality'] = quality_report
        
        # Determine overall validation status
        all_valid = all([schema_valid, types_valid, ranges_valid, consistency_valid, business_valid])
        
        if all_valid:
            validation_report['overall_status'] = 'passed'
        elif self.auto_fix and fixed_df is not None:
            validation_report['overall_status'] = 'passed_with_fixes'
        else:
            validation_report['overall_status'] = 'failed'
        
        # Final shape after fixes
        if fixed_df is not None:
            validation_report['final_shape'] = fixed_df.shape
        
        logger.info(f"Data validation complete: {validation_report['overall_status']}")
        
        return all_valid or (self.auto_fix and fixed_df is not None), validation_report, fixed_df
    
    def _validate_schema(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate data schema
        """
        schema_report = {
            'required_columns_present': True,
            'missing_required_columns': [],
            'unexpected_columns': [],
            'column_count': len(df.columns)
        }
        
        # Check required columns
        required_cols = [col for col, spec in self.expected_schema.items() if spec.get('required', False)]
        missing_required = [col for col in required_cols if col not in df.columns]
        
        if missing_required:
            schema_report['required_columns_present'] = False
            schema_report['missing_required_columns'] = missing_required
        
        # Check for unexpected columns (informational)
        expected_cols = set(self.expected_schema.keys())
        actual_cols = set(df.columns)
        unexpected = actual_cols - expected_cols
        schema_report['unexpected_columns'] = list(unexpected)
        
        is_valid = len(missing_required) == 0
        return is_valid, schema_report
    
    def _validate_data_types(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate data types
        """
        types_report = {
            'type_mismatches': {},
            'conversion_possible': {},
            'non_convertible': []
        }
        
        fixes = []
        all_valid = True
        
        for col, spec in self.expected_schema.items():
            if col not in df.columns:
                continue
            
            expected_type = spec['type']
            actual_series = df[col]
            
            if expected_type == 'numeric':
                if not pd.api.types.is_numeric_dtype(actual_series):
                    # Try to convert to numeric
                    converted, convertible = self._try_numeric_conversion(actual_series)
                    
                    if convertible:
                        types_report['conversion_possible'][col] = 'string_to_numeric'
                        fixes.append(f"convert_{col}_to_numeric")
                    else:
                        types_report['non_convertible'].append(col)
                        all_valid = False
                    
                    types_report['type_mismatches'][col] = {
                        'expected': 'numeric',
                        'actual': str(actual_series.dtype),
                        'convertible': convertible
                    }
            
            elif expected_type == 'string':
                if not pd.api.types.is_string_dtype(actual_series) and not pd.api.types.is_object_dtype(actual_series):
                    types_report['type_mismatches'][col] = {
                        'expected': 'string',
                        'actual': str(actual_series.dtype),
                        'convertible': True
                    }
                    fixes.append(f"convert_{col}_to_string")
        
        return all_valid, types_report, fixes
    
    def _try_numeric_conversion(self, series: pd.Series) -> Tuple[pd.Series, bool]:
        """
        Try to convert series to numeric
        """
        try:
            converted = pd.to_numeric(series, errors='coerce')
            # Consider conversion successful if less than 50% become NaN
            nan_pct = converted.isnull().sum() / len(converted)
            return converted, nan_pct < 0.5
        except:
            return series, False
    
    def _validate_value_ranges(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any], List[str]]:
        """
        Validate value ranges
        """
        ranges_report = {
            'out_of_range_features': {},
            'range_violations': 0,
            'total_values_checked': 0
        }
        
        fixes = []
        all_valid = True
        
        for col, spec in self.expected_schema.items():
            if col not in df.columns or 'range' not in spec:
                continue
            
            expected_range = spec['range']
            values = df[col].dropna()
            
            if len(values) == 0:
                continue
            
            # Check range violations
            out_of_range = values[(values < expected_range[0]) | (values > expected_range[1])]
            
            if len(out_of_range) > 0:
                ranges_report['out_of_range_features'][col] = {
                    'expected_range': expected_range,
                    'actual_range': (float(values.min()), float(values.max())),
                    'violations': len(out_of_range),
                    'violation_percentage': (len(out_of_range) / len(values)) * 100
                }
                
                ranges_report['range_violations'] += len(out_of_range)
                fixes.append(f"clip_{col}_to_range")
                all_valid = False
            
            ranges_report['total_values_checked'] += len(values)
        
        return all_valid, ranges_report, fixes
    
    def _validate_data_consistency(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate data consistency
        """
        consistency_report = {
            'duplicate_countries': 0,
            'missing_data_patterns': {},
            'data_distribution_issues': []
        }
        
        all_valid = True
        
        # Check for duplicate countries
        if 'country_name' in df.columns:
            duplicates = df['country_name'].duplicated().sum()
            consistency_report['duplicate_countries'] = duplicates
            if duplicates > 0:
                all_valid = False
        
        # Analyze missing data patterns
        numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
        for col in numeric_cols:
            missing_pct = (df[col].isnull().sum() / len(df)) * 100
            if missing_pct > 25:  # More than 25% missing
                consistency_report['missing_data_patterns'][col] = missing_pct
        
        # Check data distribution issues
        for col in numeric_cols:
            values = df[col].dropna()
            if len(values) > 0:
                # Check for suspicious distributions
                if values.std() == 0:
                    consistency_report['data_distribution_issues'].append(f"{col}: zero variance")
                elif values.nunique() < 3:
                    consistency_report['data_distribution_issues'].append(f"{col}: very few unique values")
        
        return all_valid, consistency_report
    
    def _validate_business_rules(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate business logic rules
        """
        business_report = {
            'rules_tested': len(self.business_rules),
            'rules_passed': 0,
            'rule_results': {}
        }
        
        all_passed = True
        
        for rule in self.business_rules:
            try:
                passed, details = rule['validator'](df)
                business_report['rule_results'][rule['name']] = {
                    'passed': passed,
                    'description': rule['description'],
                    'details': details
                }
                
                if passed:
                    business_report['rules_passed'] += 1
                else:
                    all_passed = False
                    
            except Exception as e:
                business_report['rule_results'][rule['name']] = {
                    'passed': False,
                    'description': rule['description'],
                    'error': str(e)
                }
                all_passed = False
        
        return all_passed, business_report
    
    def _validate_safety_crime_relationship(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate that safety and crime rates are inversely related
        """
        if 'safety_rate' not in df.columns or 'crime_rate' not in df.columns:
            return True, {'reason': 'columns_not_available'}
        
        # Filter to countries with both values
        both_available = df[['safety_rate', 'crime_rate']].dropna()
        
        if len(both_available) < 10:
            return True, {'reason': 'insufficient_data', 'samples': len(both_available)}
        
        # Calculate correlation
        correlation = both_available['safety_rate'].corr(both_available['crime_rate'])
        
        # Should be negative correlation
        is_valid = correlation < -0.1  # Allow some tolerance
        
        return is_valid, {
            'correlation': correlation,
            'samples_analyzed': len(both_available),
            'expected': 'negative_correlation'
        }
    
    def _validate_feature_completeness(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate that countries have reasonable feature coverage
        """
        feature_cols = [col for col in df.columns if col.endswith('_rate') or col.endswith('_index')]
        
        if not feature_cols:
            return False, {'reason': 'no_feature_columns_found'}
        
        # Calculate completeness for each country
        completeness_scores = []
        for _, row in df.iterrows():
            non_null_features = sum(1 for col in feature_cols if pd.notna(row[col]))
            completeness = non_null_features / len(feature_cols)
            completeness_scores.append(completeness)
        
        avg_completeness = np.mean(completeness_scores)
        min_completeness = np.min(completeness_scores)
        
        # At least 50% features should be available on average
        is_valid = avg_completeness >= 0.5 and min_completeness >= 0.2
        
        return is_valid, {
            'average_completeness': avg_completeness,
            'minimum_completeness': min_completeness,
            'features_analyzed': len(feature_cols),
            'countries_analyzed': len(df)
        }
    
    def _validate_value_consistency(self, df: pd.DataFrame) -> Tuple[bool, Dict[str, Any]]:
        """
        Validate internal consistency of values
        """
        issues = []
        
        # Check for countries with all zeros (suspicious)
        feature_cols = [col for col in df.columns if col.endswith('_rate') or col.endswith('_index')]
        
        for _, row in df.iterrows():
            country = row.get('country_name', 'unknown')
            feature_values = [row[col] for col in feature_cols if pd.notna(row[col])]
            
            if len(feature_values) > 3:
                # Check for all identical values (suspicious)
                if len(set(feature_values)) == 1:
                    issues.append(f"{country}: all features have identical values")
                
                # Check for impossible combinations
                if 'safety_rate' in row and 'crime_rate' in row:
                    if pd.notna(row['safety_rate']) and pd.notna(row['crime_rate']):
                        if row['safety_rate'] > 8 and row['crime_rate'] > 8:
                            issues.append(f"{country}: high safety with high crime (inconsistent)")
        
        is_valid = len(issues) == 0
        
        return is_valid, {
            'consistency_issues': issues,
            'issues_count': len(issues)
        }
    
    def _assess_feature_quality(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Assess overall feature quality
        """
        feature_cols = [col for col in df.columns if col.endswith('_rate') or col.endswith('_index')]
        
        quality_report = {
            'total_features': len(feature_cols),
            'feature_quality_scores': {},
            'overall_quality_score': 0.0,
            'quality_recommendations': []
        }
        
        total_quality = 0.0
        
        for col in feature_cols:
            values = df[col].dropna()
            
            if len(values) == 0:
                quality_score = 0.0
            else:
                # Calculate quality components
                completeness = len(values) / len(df)
                variance = values.var() if len(values) > 1 else 0
                range_usage = (values.max() - values.min()) / 10.0 if values.max() != values.min() else 0
                
                # Combined quality score
                quality_score = (completeness * 0.5 + 
                               min(variance / 5.0, 1.0) * 0.3 + 
                               range_usage * 0.2)
            
            quality_report['feature_quality_scores'][col] = {
                'score': quality_score,
                'completeness': len(values) / len(df),
                'variance': values.var() if len(values) > 1 else 0,
                'range': (float(values.min()), float(values.max())) if len(values) > 0 else (0, 0)
            }
            
            total_quality += quality_score
        
        # Overall quality score
        if len(feature_cols) > 0:
            quality_report['overall_quality_score'] = total_quality / len(feature_cols)
        
        # Generate recommendations
        low_quality_features = [col for col, info in quality_report['feature_quality_scores'].items() 
                               if info['score'] < 0.5]
        
        if low_quality_features:
            quality_report['quality_recommendations'].append(
                f"Consider improving data collection for: {', '.join(low_quality_features[:3])}"
            )
        
        if quality_report['overall_quality_score'] < 0.6:
            quality_report['quality_recommendations'].append(
                "Overall data quality could be improved through better data collection or imputation"
            )
        
        return quality_report
    
    def _apply_type_fixes(self, df: pd.DataFrame, fixes: List[str]) -> pd.DataFrame:
        """
        Apply automatic type fixes
        """
        fixed_df = df.copy()
        
        for fix in fixes:
            if fix.startswith('convert_') and fix.endswith('_to_numeric'):
                col = fix.replace('convert_', '').replace('_to_numeric', '')
                if col in fixed_df.columns:
                    fixed_df[col] = pd.to_numeric(fixed_df[col], errors='coerce')
                    logger.info(f"Converted {col} to numeric")
            
            elif fix.startswith('convert_') and fix.endswith('_to_string'):
                col = fix.replace('convert_', '').replace('_to_string', '')
                if col in fixed_df.columns:
                    fixed_df[col] = fixed_df[col].astype(str)
                    logger.info(f"Converted {col} to string")
        
        return fixed_df
    
    def _apply_range_fixes(self, df: pd.DataFrame, fixes: List[str]) -> pd.DataFrame:
        """
        Apply automatic range fixes (clipping)
        """
        fixed_df = df.copy()
        
        for fix in fixes:
            if fix.startswith('clip_') and fix.endswith('_to_range'):
                col = fix.replace('clip_', '').replace('_to_range', '')
                if col in fixed_df.columns and col in self.expected_schema:
                    range_spec = self.expected_schema[col].get('range')
                    if range_spec:
                        fixed_df[col] = fixed_df[col].clip(lower=range_spec[0], upper=range_spec[1])
                        logger.info(f"Clipped {col} to range {range_spec}")
        
        return fixed_df


