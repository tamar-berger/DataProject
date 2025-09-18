"""
Importance Mapper Module
Maps user-stated importance scores to feature weights
"""

import numpy as np
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class ImportanceMapper:
    """
    Maps user importance ratings (0-100) to normalized feature weights
    
    Handles the translation from user-friendly categories like "Safety level" 
    to technical database features like "safety_rate", "crime_rate"
    """
    
    def __init__(self, preference_mapping: Dict[str, List[str]]):
        """
        Initialize mapper with preference-to-feature mapping
        
        Args:
            preference_mapping: Maps preference names to database features
                e.g., {'Safety': ['safety_rate', 'crime_rate']}
        """
        self.preference_mapping = preference_mapping
        
    def map_importance_to_weights(self, 
                                 importance_scores: Dict[str, int]) -> Dict[str, float]:
        """
        Convert user importance scores to normalized feature weights
        
        Args:
            importance_scores: User importance ratings (0-100)
                e.g., {'Safety level': 90, 'English speaking level': 70, 'Budget friendliness': 50}
                
        Returns:
            Dictionary of feature weights summing to 1.0
        """
        feature_weights = {}
        
        # Map each importance to its corresponding features
        for preference, importance in importance_scores.items():
            if preference in self.preference_mapping:
                # Convert 0-100 scale to weight (with exponential scaling for high importance)
                weight = self._importance_to_weight(importance)
                
                # Distribute weight among features for this preference
                features = self.preference_mapping[preference]
                weight_per_feature = weight / len(features)
                
                for feature in features:
                    feature_weights[feature] = feature_weights.get(feature, 0) + weight_per_feature
            else:
                logger.warning(f"Unknown preference category: {preference}")
        
        # Normalize weights to sum to 1
        normalized_weights = self._normalize_weights(feature_weights)
        
        logger.info(f"Mapped {len(importance_scores)} importance scores to {len(normalized_weights)} features")
        return normalized_weights
    
    def _importance_to_weight(self, importance: int) -> float:
        """
        Convert importance score (0-100) to weight using exponential scaling
        
        This gives much higher weight to very important preferences (80-100)
        """
        if importance <= 0:
            return 0.0
        elif importance >= 100:
            return 1.0
        else:
            # Exponential scaling: 10→0.01, 50→0.25, 80→0.64, 100→1.0
            return (importance / 100) ** 1.5
    
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize weights to sum to 1.0
        """
        if not weights:
            return {}
        
        total_weight = sum(weights.values())
        if total_weight == 0:
            # Equal weights if all are zero
            equal_weight = 1.0 / len(weights)
            return {feature: equal_weight for feature in weights}
        
        return {feature: weight / total_weight for feature, weight in weights.items()}
    
    def get_high_importance_features(self, 
                                   importance_scores: Dict[str, int],
                                   threshold: int = 80) -> List[str]:
        """
        Get features corresponding to high-importance preferences
        
        Args:
            importance_scores: User importance ratings
            threshold: Minimum importance to be considered "high"
            
        Returns:
            List of feature names for high-importance preferences
        """
        high_importance_features = []
        
        for preference, importance in importance_scores.items():
            if importance >= threshold and preference in self.preference_mapping:
                high_importance_features.extend(self.preference_mapping[preference])
        
        return list(set(high_importance_features))  # Remove duplicates
    
    def explain_mapping(self, importance_scores: Dict[str, int]) -> str:
        """
        Generate human-readable explanation of the mapping
        """
        explanations = []
        
        # Sort by importance (highest first)
        sorted_prefs = sorted(importance_scores.items(), key=lambda x: x[1], reverse=True)
        
        for preference, importance in sorted_prefs:
            if preference in self.preference_mapping:
                features = self.preference_mapping[preference]
                feature_names = [f.replace('_rate', '').replace('_', ' ') for f in features]
                
                if importance >= 90:
                    level = "extremely important"
                elif importance >= 70:
                    level = "very important"
                elif importance >= 50:
                    level = "moderately important"
                else:
                    level = "somewhat important"
                
                explanations.append(
                    f"{preference} ({importance}/100) is {level} → "
                    f"emphasizing {', '.join(feature_names)}"
                )
        
        return "\n".join(explanations)


