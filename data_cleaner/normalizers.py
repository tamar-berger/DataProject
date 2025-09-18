"""
Data and Country Name Normalization Module

Handles:
1. Country name standardization using fuzzy matching
2. Data normalization with winsorization and scaling
3. Directional correction for "lower is better" indicators
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from fuzzywuzzy import fuzz
import re
import logging

logger = logging.getLogger(__name__)


class CountryNormalizer:
    """
    Handles country name normalization with deterministic and fuzzy matching.
    
    Implements 3-step resolution:
    1. Deterministic mapping after string cleanup
    2. Fuzzy matching with configurable threshold
    3. Rejection logging with suggestions
    """
    
    def __init__(self, country_dict: Dict[str, str], fuzzy_threshold: int = 90):
        """
        Initialize country normalizer.
        
        Args:
            country_dict: Standard country names mapping
            fuzzy_threshold: Minimum fuzzy match score for auto-acceptance (0-100)
        """
        self.country_dict = country_dict
        self.fuzzy_threshold = fuzzy_threshold
        
        # Create normalized lookup for deterministic matching
        self.normalized_lookup = {}
        for standard_name in country_dict.keys():
            # Normalize standard names for lookup
            normalized = self._normalize_string(standard_name)
            self.normalized_lookup[normalized] = standard_name
        
        # Track matching statistics
        self.match_stats = {
            'deterministic': 0,
            'fuzzy': 0,
            'rejected': 0,
            'total': 0
        }
        
        # Store rejected countries with suggestions
        self.rejections = []
    
    def _normalize_string(self, text: str) -> str:
        """
        Normalize string for deterministic matching.
        
        Args:
            text: Input string to normalize
            
        Returns:
            Cleaned and normalized string
        """
        if pd.isna(text):
            return ""
        
        # Convert to lowercase and strip whitespace
        text = str(text).strip().lower()
        
        # Remove/replace punctuation and special characters
        text = re.sub(r'[^\w\s]', '', text)
        
        # Collapse multiple whitespaces
        text = re.sub(r'\s+', '', text)
        
        return text
    
    def _fuzzy_match(self, input_name: str) -> Tuple[Optional[str], int, List[Tuple[str, int]]]:
        """
        Perform fuzzy matching against standard country names.
        
        Args:
            input_name: Country name to match
            
        Returns:
            Tuple of (best_match, score, top_3_suggestions)
        """
        best_match = None
        best_score = 0
        all_scores = []
        
        # Test against all standard country names
        for standard_name in self.country_dict.keys():
            # Use token set ratio for flexible matching
            score = fuzz.token_set_ratio(input_name.lower(), standard_name.lower())
            all_scores.append((standard_name, score))
            
            if score > best_score:
                best_score = score
                best_match = standard_name if score >= self.fuzzy_threshold else None
        
        # Get top 3 suggestions sorted by score
        top_3 = sorted(all_scores, key=lambda x: x[1], reverse=True)[:3]
        
        return best_match, best_score, top_3
    
    def normalize_country_name(self, input_name: str, allow_unknown: bool = True) -> Optional[str]:
        """
        Normalize a single country name using 3-step resolution with UNKNOWN_x fallback.
        
        Args:
            input_name: Raw country name from CSV
            allow_unknown: If True, create UNKNOWN_x ID for unmatched countries
            
        Returns:
            Standardized country name or UNKNOWN_x ID
        """
        self.match_stats['total'] += 1
        
        if pd.isna(input_name) or input_name == "":
            if allow_unknown:
                unknown_id = f"UNKNOWN_{len(self.rejections) + 1:03d}"
                self.rejections.append({
                    'original_name': 'NULL_OR_EMPTY',
                    'assigned_id': unknown_id,
                    'best_score': 0,
                    'suggestions': []
                })
                self.match_stats['unknown_assigned'] = self.match_stats.get('unknown_assigned', 0) + 1
                return unknown_id
            return None
        
        original_name = str(input_name).strip()
        
        # Step 1: Deterministic matching
        normalized = self._normalize_string(original_name)
        if normalized in self.normalized_lookup:
            self.match_stats['deterministic'] += 1
            logger.debug(f"Deterministic match: '{original_name}' -> '{self.normalized_lookup[normalized]}'")
            return self.normalized_lookup[normalized]
        
        # Step 2: Fuzzy matching
        best_match, score, suggestions = self._fuzzy_match(original_name)
        if best_match is not None:
            self.match_stats['fuzzy'] += 1
            logger.info(f"Fuzzy match: '{original_name}' -> '{best_match}' (score: {score})")
            return best_match
        
        # Step 3: Create UNKNOWN_x ID or reject
        if allow_unknown:
            unknown_id = f"UNKNOWN_{len(self.rejections) + 1:03d}"
            rejection_entry = {
                'original_name': original_name,
                'assigned_id': unknown_id,
                'best_score': score,
                'suggestions': suggestions
            }
            self.rejections.append(rejection_entry)
            self.match_stats['unknown_assigned'] = self.match_stats.get('unknown_assigned', 0) + 1
            logger.warning(f"Country assigned UNKNOWN ID: '{original_name}' -> '{unknown_id}' (best score: {score})")
            return unknown_id
        else:
            # Legacy behavior: reject completely
            self.match_stats['rejected'] += 1
            rejection_entry = {
                'original_name': original_name,
                'best_score': score,
                'suggestions': suggestions
            }
            self.rejections.append(rejection_entry)
            logger.warning(f"Country rejected: '{original_name}' (best score: {score})")
            return None
    
    def get_match_report(self) -> Dict:
        """
        Generate comprehensive matching report.
        
        Returns:
            Dictionary with matching statistics and rejection details
        """
        total = self.match_stats['total']
        if total == 0:
            return {'error': 'No countries processed'}
        
        return {
            'total_countries': total,
            'deterministic_matches': self.match_stats['deterministic'],
            'fuzzy_matches': self.match_stats['fuzzy'],
            'rejections': self.match_stats['rejected'],
            'match_rate': (self.match_stats['deterministic'] + self.match_stats['fuzzy']) / total,
            'rejection_details': self.rejections
        }


class DataNormalizer:
    """
    Handles numeric data normalization with winsorization and scaling.
    
    Implements robust min-max normalization:
    1. Winsorize at configurable percentiles
    2. Scale to [0,1] range
    3. Invert for "lower is better" indicators
    """
    
    def __init__(self, winsor_lower: float = 1.0, winsor_upper: float = 99.0):
        """
        Initialize data normalizer.
        
        Args:
            winsor_lower: Lower percentile for winsorization (0-100)
            winsor_upper: Upper percentile for winsorization (0-100)
        """
        self.winsor_lower = winsor_lower
        self.winsor_upper = winsor_upper
        
        # Track normalization statistics per column
        self.normalization_stats = {}
        
        # Define indicators where "lower is better"
        self.invert_indicators = {
            'crime_index',
            'cost_of_living_index',
            'cost_of_living'  # Alternative naming
        }
    
    def _winsorize_column(self, series: pd.Series, column_name: str) -> Tuple[pd.Series, Dict]:
        """
        Apply winsorization to a numeric series.
        
        Args:
            series: Pandas series to winsorize
            column_name: Name of the column for logging
            
        Returns:
            Tuple of (winsorized_series, statistics_dict)
        """
        # Remove NaN values for percentile calculation
        valid_data = series.dropna()
        
        if len(valid_data) == 0:
            return series, {'error': 'No valid data for winsorization'}
        
        # Calculate percentiles
        p_lower = np.percentile(valid_data, self.winsor_lower)
        p_upper = np.percentile(valid_data, self.winsor_upper)
        
        # Apply winsorization
        winsorized = series.clip(lower=p_lower, upper=p_upper)
        
        # Calculate statistics
        stats = {
            'original_min': series.min(),
            'original_max': series.max(),
            'original_mean': series.mean(),
            'original_std': series.std(),
            'winsor_lower_bound': p_lower,
            'winsor_upper_bound': p_upper,
            'values_clipped_lower': (series < p_lower).sum(),
            'values_clipped_upper': (series > p_upper).sum(),
            'total_clipped': ((series < p_lower) | (series > p_upper)).sum()
        }
        
        logger.info(f"Winsorized {column_name}: {stats['total_clipped']} values clipped")
        
        return winsorized, stats
    
    def _normalize_to_unit_range(self, series: pd.Series, winsor_stats: Dict) -> pd.Series:
        """
        Normalize winsorized data to [0,1] range.
        
        Args:
            series: Winsorized series
            winsor_stats: Statistics from winsorization
            
        Returns:
            Normalized series in [0,1] range
        """
        p_min = winsor_stats['winsor_lower_bound']
        p_max = winsor_stats['winsor_upper_bound']
        
        # Avoid division by zero
        if p_max == p_min:
            logger.warning(f"Constant values detected after winsorization: {p_min}")
            return pd.Series(0.5, index=series.index)  # Middle value for constants
        
        # Min-max normalization
        normalized = (series - p_min) / (p_max - p_min)
        
        # Clip to [0,1] to handle any floating point precision issues
        normalized = normalized.clip(0, 1)
        
        return normalized
    
    def normalize_column(self, series: pd.Series, column_name: str) -> Tuple[pd.Series, Dict]:
        """
        Normalize a complete column with winsorization and scaling.
        
        Args:
            series: Input data series
            column_name: Name of the column
            
        Returns:
            Tuple of (normalized_series, comprehensive_statistics)
        """
        logger.info(f"Normalizing column: {column_name}")
        
        # Step 1: Winsorization
        winsorized, winsor_stats = self._winsorize_column(series, column_name)
        
        # Step 2: Unit range normalization
        normalized = self._normalize_to_unit_range(winsorized, winsor_stats)
        
        # Step 3: Directional correction for "lower is better" indicators
        should_invert = any(indicator in column_name.lower() for indicator in self.invert_indicators)
        if should_invert:
            normalized = 1 - normalized
            logger.info(f"Inverted {column_name} (lower is better)")
        
        # Compile comprehensive statistics
        final_stats = {
            **winsor_stats,
            'inverted': should_invert,
            'final_min': normalized.min(),
            'final_max': normalized.max(),
            'final_mean': normalized.mean(),
            'final_std': normalized.std(),
            'missing_count': series.isna().sum(),
            'missing_rate': series.isna().sum() / len(series)
        }
        
        # Store statistics for reporting
        self.normalization_stats[column_name] = final_stats
        
        return normalized, final_stats
    
    def get_normalization_report(self) -> Dict:
        """
        Generate comprehensive normalization report.
        
        Returns:
            Dictionary with statistics for all normalized columns
        """
        return {
            'winsorization_percentiles': {
                'lower': self.winsor_lower,
                'upper': self.winsor_upper
            },
            'inverted_indicators': list(self.invert_indicators),
            'column_statistics': self.normalization_stats
        }