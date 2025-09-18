"""
Feature Processing Module
Handles data preprocessing, normalization, and feature engineering for country data
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.feature_selection import VarianceThreshold, SelectKBest, f_regression
import logging

logger = logging.getLogger(__name__)


class FeatureProcessor:
    """
    Comprehensive feature processing pipeline for country recommendation data.
    
    Handles:
    - Missing value imputation
    - Outlier detection and treatment
    - Feature normalization and scaling
    - Feature selection and engineering
    - Data quality validation
    """
    
    def __init__(self,
                 normalization_method: str = 'minmax',
                 imputation_strategy: str = 'median',
                 outlier_method: str = 'iqr',
                 feature_selection: bool = False):
        """
        Initialize feature processor
        
        Args:
            normalization_method: 'minmax', 'standard', 'robust'
            imputation_strategy: 'mean', 'median', 'knn', 'forward_fill'
            outlier_method: 'iqr', 'zscore', 'isolation_forest'
            feature_selection: Whether to apply feature selection
        """
        self.normalization_method = normalization_method
        self.imputation_strategy = imputation_strategy
        self.outlier_method = outlier_method
        self.feature_selection = feature_selection
        
        # Initialize processors
        self.scaler = self._get_scaler()
        self.imputer = self._get_imputer()
        self.feature_selector = None
        
        # Store processing metadata
        self.processing_stats = {}
        self.feature_names = []
        self.outlier_indices = []
        
    def _get_scaler(self):
        """Get appropriate scaler based on method"""
        if self.normalization_method == 'minmax':
            return MinMaxScaler(feature_range=(0, 1))  # Keep 0-1 scale as data is already normalized
        elif self.normalization_method == 'standard':
            return StandardScaler()
        elif self.normalization_method == 'robust':
            return RobustScaler()
        elif self.normalization_method == 'none':
            return None  # Skip normalization if data is already properly scaled
        else:
            raise ValueError(f"Unknown normalization method: {self.normalization_method}")
    
    def _get_imputer(self):
        """Get appropriate imputer based on strategy"""
        if self.imputation_strategy in ['mean', 'median', 'most_frequent']:
            return SimpleImputer(strategy=self.imputation_strategy)
        elif self.imputation_strategy == 'knn':
            return KNNImputer(n_neighbors=5)
        else:
            return SimpleImputer(strategy='median')
    
    def process_features(self, 
                        countries_df: pd.DataFrame,
                        target_features: Optional[List[str]] = None) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Complete feature processing pipeline
        
        Args:
            countries_df: Raw country data
            target_features: Specific features to process (if None, auto-detect)
            
        Returns:
            Tuple of (processed_dataframe, processing_metadata)
        """
        logger.info("Starting feature processing pipeline")
        
        # Step 1: Identify and extract features
        feature_df, feature_names = self._extract_features(countries_df, target_features)
        self.feature_names = feature_names
        
        # Step 2: Data quality assessment
        quality_report = self._assess_data_quality(feature_df)
        
        # Step 3: Handle missing values
        imputed_df = self._handle_missing_values(feature_df)
        
        # Step 4: Detect and handle outliers
        cleaned_df, outlier_info = self._handle_outliers(imputed_df)
        
        # Step 5: Normalize features
        normalized_df = self._normalize_features(cleaned_df)
        
        # Step 6: Feature selection (optional)
        if self.feature_selection:
            selected_df, selection_info = self._select_features(normalized_df)
        else:
            selected_df = normalized_df
            selection_info = {'method': 'none', 'selected_features': feature_names}
        
        # Step 7: Create final processed dataframe
        processed_df = self._create_final_dataframe(countries_df, selected_df)
        
        # Compile processing metadata
        processing_metadata = {
            'original_shape': countries_df.shape,
            'processed_shape': processed_df.shape,
            'feature_names': self.feature_names,
            'quality_report': quality_report,
            'outlier_info': outlier_info,
            'selection_info': selection_info,
            'processing_stats': self.processing_stats
        }
        
        logger.info(f"Feature processing complete: {len(feature_names)} features processed")
        return processed_df, processing_metadata
    
    def _extract_features(self, 
                         countries_df: pd.DataFrame,
                         target_features: Optional[List[str]]) -> Tuple[pd.DataFrame, List[str]]:
        """
        Extract and identify feature columns
        """
        if target_features:
            # Use explicitly specified features
            feature_cols = [col for col in target_features if col in countries_df.columns]
        else:
            # Auto-detect numeric feature columns
            feature_cols = [col for col in countries_df.columns 
                           if col.endswith('_rate') or col.endswith('_index') or col.endswith('_score')]
            
            # Add other numeric columns that aren't metadata
            numeric_cols = countries_df.select_dtypes(include=[np.number]).columns
            metadata_cols = ['id', 'country_id', 'year', 'population']
            
            for col in numeric_cols:
                if (col not in feature_cols and 
                    col not in metadata_cols and 
                    not col.startswith('country')):
                    feature_cols.append(col)
        
        if not feature_cols:
            raise ValueError("No feature columns found in the data")
        
        feature_df = countries_df[feature_cols].copy()
        
        logger.info(f"Extracted {len(feature_cols)} feature columns: {feature_cols}")
        return feature_df, feature_cols
    
    def _assess_data_quality(self, feature_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Assess data quality and generate report
        """
        quality_report = {
            'total_features': len(feature_df.columns),
            'total_samples': len(feature_df),
            'missing_data': {},
            'data_types': {},
            'value_ranges': {},
            'potential_issues': []
        }
        
        for col in feature_df.columns:
            # Missing data analysis
            missing_count = feature_df[col].isnull().sum()
            missing_pct = (missing_count / len(feature_df)) * 100
            quality_report['missing_data'][col] = {
                'count': missing_count,
                'percentage': missing_pct
            }
            
            # Data type
            quality_report['data_types'][col] = str(feature_df[col].dtype)
            
            # Value ranges (for numeric columns)
            if pd.api.types.is_numeric_dtype(feature_df[col]):
                non_null_values = feature_df[col].dropna()
                if len(non_null_values) > 0:
                    quality_report['value_ranges'][col] = {
                        'min': float(non_null_values.min()),
                        'max': float(non_null_values.max()),
                        'mean': float(non_null_values.mean()),
                        'std': float(non_null_values.std())
                    }
            
            # Identify potential issues
            if missing_pct > 50:
                quality_report['potential_issues'].append(f"{col}: >50% missing data")
            
            if pd.api.types.is_numeric_dtype(feature_df[col]):
                non_null_values = feature_df[col].dropna()
                if len(non_null_values) > 0:
                    # Check for extreme outliers
                    q1, q3 = non_null_values.quantile([0.25, 0.75])
                    iqr = q3 - q1
                    outliers = non_null_values[(non_null_values < q1 - 3*iqr) | 
                                             (non_null_values > q3 + 3*iqr)]
                    if len(outliers) > len(non_null_values) * 0.1:
                        quality_report['potential_issues'].append(f"{col}: >10% extreme outliers")
        
        return quality_report
    
    def _handle_missing_values(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        """
        Handle missing values using specified imputation strategy
        """
        logger.info(f"Handling missing values using {self.imputation_strategy} strategy")
        
        if self.imputation_strategy == 'forward_fill':
            # Forward fill followed by median imputation for remaining NaNs
            imputed_df = feature_df.ffill().fillna(feature_df.median())
        else:
            # Use sklearn imputers
            imputed_values = self.imputer.fit_transform(feature_df)
            imputed_df = pd.DataFrame(imputed_values, 
                                    columns=feature_df.columns, 
                                    index=feature_df.index)
        
        # Store imputation statistics
        self.processing_stats['imputation'] = {
            'strategy': self.imputation_strategy,
            'original_missing': feature_df.isnull().sum().to_dict(),
            'remaining_missing': imputed_df.isnull().sum().to_dict()
        }
        
        return imputed_df
    
    def _handle_outliers(self, feature_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Detect and handle outliers
        """
        logger.info(f"Detecting outliers using {self.outlier_method} method")
        
        outlier_info = {
            'method': self.outlier_method,
            'outliers_by_feature': {},
            'total_outliers_detected': 0
        }
        
        cleaned_df = feature_df.copy()
        
        for col in feature_df.columns:
            if pd.api.types.is_numeric_dtype(feature_df[col]):
                outlier_mask = self._detect_outliers(feature_df[col])
                outlier_count = outlier_mask.sum()
                
                outlier_info['outliers_by_feature'][col] = {
                    'count': outlier_count,
                    'percentage': (outlier_count / len(feature_df)) * 100
                }
                
                # Handle outliers by capping to reasonable bounds
                if outlier_count > 0:
                    q1, q3 = feature_df[col].quantile([0.05, 0.95])  # Use 5-95 percentile for capping
                    cleaned_df[col] = feature_df[col].clip(lower=q1, upper=q3)
        
        outlier_info['total_outliers_detected'] = sum(
            info['count'] for info in outlier_info['outliers_by_feature'].values()
        )
        
        return cleaned_df, outlier_info
    
    def _detect_outliers(self, series: pd.Series) -> pd.Series:
        """
        Detect outliers in a single feature
        """
        if self.outlier_method == 'iqr':
            q1, q3 = series.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return (series < lower_bound) | (series > upper_bound)
        
        elif self.outlier_method == 'zscore':
            z_scores = np.abs((series - series.mean()) / series.std())
            return z_scores > 3
        
        else:
            # Default to IQR method
            q1, q3 = series.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            return (series < lower_bound) | (series > upper_bound)
    
    def _normalize_features(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        """
        Normalize features using specified method
        """
        logger.info(f"Normalizing features using {self.normalization_method} method")
        
        # Skip normalization if method is 'none' or data is already normalized
        if self.normalization_method == 'none' or self.scaler is None:
            logger.info("Skipping normalization - data already in 0-1 range")
            return feature_df
        
        # Apply scaling
        scaled_values = self.scaler.fit_transform(feature_df)
        
        # Create normalized dataframe
        normalized_df = pd.DataFrame(scaled_values,
                                   columns=feature_df.columns,
                                   index=feature_df.index)
        
        # Store normalization statistics
        self.processing_stats['normalization'] = {
            'method': self.normalization_method,
            'feature_ranges': {}
        }
        
        for col in normalized_df.columns:
            self.processing_stats['normalization']['feature_ranges'][col] = {
                'min': float(normalized_df[col].min()),
                'max': float(normalized_df[col].max()),
                'mean': float(normalized_df[col].mean())
            }
        
        return normalized_df
    
    def _select_features(self, feature_df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Apply feature selection if enabled
        """
        logger.info("Applying feature selection")
        
        # Simple variance-based feature selection
        selector = VarianceThreshold(threshold=0.01)  # Remove near-zero variance features
        selected_features = selector.fit_transform(feature_df)
        
        # Get selected feature names
        selected_mask = selector.get_support()
        selected_feature_names = [name for name, selected in zip(feature_df.columns, selected_mask) if selected]
        
        selected_df = pd.DataFrame(selected_features,
                                 columns=selected_feature_names,
                                 index=feature_df.index)
        
        selection_info = {
            'method': 'variance_threshold',
            'original_features': len(feature_df.columns),
            'selected_features': selected_feature_names,
            'num_selected': len(selected_feature_names),
            'removed_features': [name for name, selected in zip(feature_df.columns, selected_mask) if not selected]
        }
        
        return selected_df, selection_info
    
    def _create_final_dataframe(self, 
                               original_df: pd.DataFrame,
                               processed_features: pd.DataFrame) -> pd.DataFrame:
        """
        Combine processed features with original metadata
        """
        # Start with processed features
        final_df = processed_features.copy()
        
        # Add essential metadata columns
        metadata_cols = ['country_name', 'country']
        for col in metadata_cols:
            if col in original_df.columns:
                final_df[col] = original_df[col].values
                break  # Only need one country identifier
        
        # Ensure country_name column exists
        if 'country_name' not in final_df.columns and 'country' in final_df.columns:
            final_df['country_name'] = final_df['country']
        
        return final_df
    
    def transform_new_data(self, new_data: pd.DataFrame) -> pd.DataFrame:
        """
        Apply learned transformations to new data
        """
        if not hasattr(self.scaler, 'scale_'):
            raise ValueError("Feature processor must be fitted before transforming new data")
        
        # Extract same features
        feature_df = new_data[self.feature_names].copy()
        
        # Apply same imputation
        imputed_values = self.imputer.transform(feature_df)
        imputed_df = pd.DataFrame(imputed_values, columns=self.feature_names, index=feature_df.index)
        
        # Apply same normalization
        normalized_values = self.scaler.transform(imputed_df)
        normalized_df = pd.DataFrame(normalized_values, columns=self.feature_names, index=imputed_df.index)
        
        # Create final dataframe
        final_df = self._create_final_dataframe(new_data, normalized_df)
        
        return final_df
    
    def get_feature_importance_scores(self, target_values: Optional[pd.Series] = None) -> Dict[str, float]:
        """
        Calculate feature importance scores (if target values provided)
        """
        if target_values is None:
            # Return uniform importance
            return {feature: 1.0/len(self.feature_names) for feature in self.feature_names}
        
        # Use statistical correlation as importance
        importance_scores = {}
        for feature in self.feature_names:
            correlation = abs(target_values.corr(pd.Series(target_values.index, index=target_values.index)))
            importance_scores[feature] = correlation if not pd.isna(correlation) else 0.0
        
        return importance_scores


