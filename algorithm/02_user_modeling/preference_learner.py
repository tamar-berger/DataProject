"""
Preference Learning Module
Learns user feature weights from historical country ratings using regression
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.linear_model import Ridge, LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
import logging

logger = logging.getLogger(__name__)


class PreferenceLearner:
    """
    Learns user preferences from historical ratings using regularized regression
    
    Key insight: If a user rates countries highly, we can infer which features
    they value by looking at the feature patterns of their highly-rated countries.
    """
    
    def __init__(self, 
                 alpha: float = 1.0,
                 min_ratings: int = 3,
                 confidence_decay: float = 0.1):
        """
        Initialize preference learner
        
        Args:
            alpha: Ridge regression regularization strength
            min_ratings: Minimum ratings needed for learning
            confidence_decay: How much to reduce confidence for sparse data
        """
        self.alpha = alpha
        self.min_ratings = min_ratings
        self.confidence_decay = confidence_decay
        self.scaler = StandardScaler()
        
    def learn_preferences(self, 
                         user_ratings: Dict[str, float],
                         country_features: pd.DataFrame) -> Tuple[Dict[str, float], float]:
        """
        Learn user feature preferences from ratings
        
        Args:
            user_ratings: {country_name: rating} dictionary (1-5 scale)
            country_features: DataFrame with country features
            
        Returns:
            Tuple of (learned_weights, confidence_score)
        """
        if len(user_ratings) < self.min_ratings:
            logger.warning(f"Only {len(user_ratings)} ratings, below minimum {self.min_ratings}")
            return {}, 0.0
        
        # Prepare training data
        X, y, feature_names = self._prepare_training_data(user_ratings, country_features)
        
        if len(X) == 0:
            logger.warning("No matching countries found in feature data")
            return {}, 0.0
        
        # Normalize features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Ridge regression to learn feature weights
        model = Ridge(alpha=self.alpha, random_state=42)
        model.fit(X_scaled, y)
        
        # Extract learned weights
        learned_weights = dict(zip(feature_names, model.coef_))
        
        # Calculate confidence based on model performance and data quantity
        confidence = self._calculate_confidence(model, X_scaled, y, len(user_ratings))
        
        # Normalize weights to sum to 1
        normalized_weights = self._normalize_weights(learned_weights)
        
        logger.info(f"Learned preferences with {confidence:.3f} confidence from {len(user_ratings)} ratings")
        return normalized_weights, confidence
    
    def _prepare_training_data(self, 
                              user_ratings: Dict[str, float],
                              country_features: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare X, y training data from user ratings and country features
        """
        # Find countries that exist in both ratings and features
        rated_countries = set(user_ratings.keys())
        available_countries = set(country_features['country_name'])
        valid_countries = rated_countries.intersection(available_countries)
        
        if not valid_countries:
            return np.array([]), np.array([]), []
        
        # Filter to valid countries
        filtered_features = country_features[
            country_features['country_name'].isin(valid_countries)
        ].copy()
        
        # Get feature columns (exclude metadata)
        feature_cols = [col for col in filtered_features.columns 
                       if col.endswith('_rate') or col.endswith('_index')]
        
        # Build X matrix and y vector
        X_list = []
        y_list = []
        
        for _, row in filtered_features.iterrows():
            country_name = row['country_name']
            if country_name in user_ratings:
                # Features as input
                features = [row[col] for col in feature_cols]
                X_list.append(features)
                
                # Normalize rating from 1-5 scale to 0.2-1.0 scale
                # 1 -> 0.2, 2 -> 0.4, 3 -> 0.6, 4 -> 0.8, 5 -> 1.0
                raw_rating = user_ratings[country_name]
                normalized_rating = raw_rating * 0.2
                y_list.append(normalized_rating)
        
        return np.array(X_list), np.array(y_list), feature_cols
    
    def _calculate_confidence(self, 
                            model, 
                            X: np.ndarray, 
                            y: np.ndarray, 
                            num_ratings: int) -> float:
        """
        Calculate confidence in learned preferences
        """
        try:
            # Simplified confidence calculation to avoid expensive cross-validation
            # Use training R² score as base confidence (faster than CV)
            y_pred = model.predict(X)
            ss_res = np.sum((y - y_pred) ** 2)
            ss_tot = np.sum((y - np.mean(y)) ** 2)
            r2_score = 1 - (ss_res / (ss_tot + 1e-10))  # Add small value to avoid division by zero
            base_confidence = max(0, r2_score)
            
            # Adjust for sample size (more ratings = higher confidence)
            sample_confidence = min(1.0, num_ratings / 10.0)
            
            # Combined confidence
            confidence = 0.7 * base_confidence + 0.3 * sample_confidence
            
        except Exception as e:
            logger.warning(f"Could not calculate confidence: {e}")
            confidence = max(0.2, min(0.8, num_ratings / 10.0))
        
        return confidence
    
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Normalize weights to be positive and sum to 1
        """
        if not weights:
            return {}
        
        # Take absolute values (we want magnitude of importance)
        abs_weights = {k: abs(v) for k, v in weights.items()}
        
        # Normalize to sum to 1
        total = sum(abs_weights.values())
        if total == 0:
            # Equal weights if all are zero
            return {k: 1.0/len(abs_weights) for k in abs_weights}
        
        normalized = {k: v/total for k, v in abs_weights.items()}
        
        return normalized
    
    def predict_rating(self, 
                      country_features: np.ndarray,
                      learned_weights: Dict[str, float]) -> float:
        """
        Predict user rating for a country given learned preferences
        
        Args:
            country_features: Feature vector for country
            learned_weights: Learned feature weights
            
        Returns:
            Predicted rating (1-5 scale)
        """
        if not learned_weights:
            return 3.0  # Neutral rating
        
        # Calculate weighted score
        score = sum(feature * learned_weights.get(f'feature_{i}', 0) 
                   for i, feature in enumerate(country_features))
        
        # Convert normalized score (0.2-1.0) back to 1-5 rating scale
        # 0.2 -> 1, 0.4 -> 2, 0.6 -> 3, 0.8 -> 4, 1.0 -> 5
        rating = np.clip(score / 0.2, 1, 5)
        
        return rating


