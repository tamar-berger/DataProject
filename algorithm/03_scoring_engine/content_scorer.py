"""
Content-Based Scoring Module
Scores countries based on feature matching with user preferences
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ContentBasedScorer:
    """
    Scores countries using weighted feature matching.
    
    Core algorithm: weighted dot product between user preference weights 
    and normalized country features.
    """
    
    def __init__(self, 
                 feature_columns: Optional[List[str]] = None,
                 score_scaling: str = 'linear'):
        """
        Initialize content-based scorer
        
        Args:
            feature_columns: List of feature columns to use for scoring
            score_scaling: How to scale final scores ('linear', 'sigmoid', 'exponential')
        """
        self.feature_columns = feature_columns
        self.score_scaling = score_scaling
        
    def score_countries(self, 
                       countries_df: pd.DataFrame,
                       user_weights: Dict[str, float],
                       normalize_features: bool = True) -> Dict[str, float]:
        """
        Score all countries based on user preference weights
        
        Args:
            countries_df: DataFrame with country features
            user_weights: Dictionary mapping feature names to weights (0-1)
            normalize_features: Whether to normalize features to 0-1 range
            
        Returns:
            Dictionary mapping country names to scores (0-1)
        """
        if countries_df.empty or not user_weights:
            return {}
        
        # Determine feature columns to use
        available_features = self._get_available_features(countries_df, user_weights)
        if not available_features:
            logger.warning("No matching features found between user weights and country data")
            return {}
        
        scores = {}
        
        for _, row in countries_df.iterrows():
            country_name = row.get('country_name', row.get('country', 'Unknown'))
            
            # Calculate weighted score for this country
            country_score = self._calculate_country_score(
                row, available_features, user_weights, normalize_features
            )
            
            # Apply score scaling
            final_score = self._apply_score_scaling(country_score)
            scores[country_name] = final_score
        
        logger.info(f"Scored {len(scores)} countries using {len(available_features)} features")
        return scores
    
    def _get_available_features(self, 
                               countries_df: pd.DataFrame,
                               user_weights: Dict[str, float]) -> List[str]:
        """
        Get features that exist in both user weights and country data
        """
        if self.feature_columns:
            # Use explicitly specified features
            available_features = [f for f in self.feature_columns 
                                if f in countries_df.columns and f in user_weights]
        else:
            # Auto-detect feature columns
            country_features = set(countries_df.columns)
            weight_features = set(user_weights.keys())
            available_features = list(country_features.intersection(weight_features))
        
        return available_features
    
    def _calculate_country_score(self,
                                country_row: pd.Series,
                                feature_names: List[str],
                                user_weights: Dict[str, float],
                                normalize_features: bool) -> float:
        """
        Calculate weighted score for a single country
        """
        weighted_score = 0.0
        total_weight = 0.0
        
        for feature in feature_names:
            feature_value = country_row.get(feature, 0)
            weight = user_weights.get(feature, 0)
            
            # Skip if either value is invalid
            if pd.isna(feature_value) or weight <= 0:
                continue
            
            # Normalize feature value if requested
            if normalize_features:
                # Features are already in 0-1 range, just ensure bounds
                normalized_value = max(0, min(1, feature_value))
            else:
                normalized_value = feature_value
            
            # Add weighted contribution
            weighted_score += weight * normalized_value
            total_weight += weight
        
        # Avoid division by zero
        if total_weight == 0:
            return 0.0
        
        # Return normalized weighted average
        return weighted_score / total_weight
    
    def _apply_score_scaling(self, raw_score: float) -> float:
        """
        Apply scaling transformation to raw score
        """
        if self.score_scaling == 'linear':
            return np.clip(raw_score, 0, 1)
        
        elif self.score_scaling == 'sigmoid':
            # Sigmoid scaling: emphasizes mid-range differences
            return 1 / (1 + np.exp(-10 * (raw_score - 0.5)))
        
        elif self.score_scaling == 'exponential':
            # Exponential scaling: emphasizes high scores
            return (raw_score ** 2) if raw_score > 0 else 0
        
        else:
            return np.clip(raw_score, 0, 1)
    
    def explain_score(self,
                     country_name: str,
                     country_row: pd.Series,
                     user_weights: Dict[str, float]) -> Dict[str, float]:
        """
        Break down score calculation for explainability
        
        Returns:
            Dictionary with feature contributions to final score
        """
        available_features = self._get_available_features(
            pd.DataFrame([country_row]), user_weights
        )
        
        contributions = {}
        total_weight = sum(user_weights.get(f, 0) for f in available_features)
        
        for feature in available_features:
            feature_value = country_row.get(feature, 0)
            weight = user_weights.get(feature, 0)
            
            if not pd.isna(feature_value) and weight > 0:
                # Features are already in 0-1 range, just ensure bounds
                normalized_value = max(0, min(1, feature_value))
                contribution = (weight / total_weight) * normalized_value if total_weight > 0 else 0
                contributions[feature] = contribution
        
        return contributions


