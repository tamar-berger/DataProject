"""
Profile Builder Module
Combines learned preferences and stated importance into unified user profile
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
import logging

from .preference_learner import PreferenceLearner
from .importance_mapper import ImportanceMapper

logger = logging.getLogger(__name__)


class UserProfile:
    """
    Represents a complete user preference profile
    """
    def __init__(self,
                 user_id: str,
                 feature_weights: Dict[str, float],
                 learned_weights: Dict[str, float],
                 stated_weights: Dict[str, float],
                 confidence: float,
                 high_importance_features: List[str],
                 num_ratings: int = 0):
        self.user_id = user_id
        self.feature_weights = feature_weights  # Final combined weights
        self.learned_weights = learned_weights  # From ratings history
        self.stated_weights = stated_weights   # From importance scores
        self.confidence = confidence           # Confidence in learned weights
        self.high_importance_features = high_importance_features  # For constraints
        self.num_ratings = num_ratings
    
    def __repr__(self):
        return f"UserProfile(user_id='{self.user_id}', confidence={self.confidence:.3f}, num_ratings={self.num_ratings})"


class UserProfileBuilder:
    """
    Builds comprehensive user profiles by combining multiple data sources
    
    Key innovation: Adaptively weights learned vs stated preferences based on
    confidence and amount of historical data
    """
    
    def __init__(self, 
                 preference_mapping: Dict[str, List[str]],
                 max_learned_weight: float = 0.8,
                 min_ratings_threshold: int = 3):
        """
        Initialize profile builder
        
        Args:
            preference_mapping: Maps preference categories to features
            max_learned_weight: Maximum weight for learned preferences
            min_ratings_threshold: Minimum ratings needed for learning
        """
        self.preference_mapping = preference_mapping
        self.max_learned_weight = max_learned_weight
        self.min_ratings_threshold = min_ratings_threshold
        
        # Initialize components
        self.preference_learner = PreferenceLearner(min_ratings=min_ratings_threshold)
        self.importance_mapper = ImportanceMapper(preference_mapping)
    
    def build_profile(self,
                     user_id: str,
                     importance_scores: Dict[str, int],
                     user_ratings: Optional[Dict[str, float]] = None,
                     country_features = None) -> UserProfile:
        """
        Build complete user profile from available data
        
        Args:
            user_id: Unique user identifier
            importance_scores: User-stated importance (1-10) for each category
            user_ratings: Historical country ratings (1-5) - optional
            country_features: DataFrame with country features for learning
            
        Returns:
            Complete UserProfile object
        """
        logger.info(f"Building profile for user {user_id}")
        
        # Step 1: Map stated importance to feature weights
        stated_weights = self.importance_mapper.map_importance_to_weights(importance_scores)
        
        # Step 2: Learn preferences from ratings (if available)
        learned_weights = {}
        confidence = 0.0
        
        if user_ratings and country_features is not None and len(user_ratings) >= self.min_ratings_threshold:
            learned_weights, confidence = self.preference_learner.learn_preferences(
                user_ratings, country_features
            )
        
        # Step 3: Combine learned and stated preferences
        final_weights = self._combine_preferences(stated_weights, learned_weights, confidence)
        
        # Step 4: Identify high-importance features for constraints
        high_importance_features = self.importance_mapper.get_high_importance_features(importance_scores)
        
        # Create profile
        profile = UserProfile(
            user_id=user_id,
            feature_weights=final_weights,
            learned_weights=learned_weights,
            stated_weights=stated_weights,
            confidence=confidence,
            high_importance_features=high_importance_features,
            num_ratings=len(user_ratings) if user_ratings else 0
        )
        
        logger.info(f"Built profile: {profile}")
        return profile
    
    def _combine_preferences(self,
                           stated_weights: Dict[str, float],
                           learned_weights: Dict[str, float],
                           confidence: float) -> Dict[str, float]:
        """
        Intelligently combine stated and learned preferences
        
        Strategy:
        - High confidence learned weights → mostly use learned
        - Low confidence or no learning → mostly use stated
        - Adaptive weighting based on confidence
        """
        if not learned_weights or confidence < 0.1:
            # No learned data or very low confidence → use stated only
            logger.info("Using stated preferences only (no/low confidence learned data)")
            return stated_weights.copy()
        
        # Calculate mixing weight for learned preferences
        learned_alpha = min(self.max_learned_weight, confidence * self.max_learned_weight)
        stated_alpha = 1.0 - learned_alpha
        
        logger.info(f"Mixing preferences: {learned_alpha:.3f} learned + {stated_alpha:.3f} stated")
        
        # Get all unique features
        all_features = set(stated_weights.keys()) | set(learned_weights.keys())
        
        # Combine weights
        combined_weights = {}
        for feature in all_features:
            stated_weight = stated_weights.get(feature, 0.0)
            learned_weight = learned_weights.get(feature, 0.0)
            
            combined_weight = (learned_alpha * learned_weight + 
                             stated_alpha * stated_weight)
            
            if combined_weight > 0:
                combined_weights[feature] = combined_weight
        
        # Normalize to sum to 1
        total = sum(combined_weights.values())
        if total > 0:
            combined_weights = {k: v/total for k, v in combined_weights.items()}
        
        return combined_weights
    
    def update_profile(self,
                      profile: UserProfile,
                      new_ratings: Dict[str, float],
                      country_features) -> UserProfile:
        """
        Update existing profile with new ratings
        
        Args:
            profile: Existing user profile
            new_ratings: New country ratings to incorporate
            country_features: Country feature data for learning
            
        Returns:
            Updated UserProfile
        """
        # Merge new ratings with existing (if any)
        all_ratings = new_ratings.copy()
        
        # Re-learn preferences with updated ratings
        learned_weights, confidence = self.preference_learner.learn_preferences(
            all_ratings, country_features
        )
        
        # Re-combine with stated preferences
        final_weights = self._combine_preferences(
            profile.stated_weights, learned_weights, confidence
        )
        
        # Create updated profile
        updated_profile = UserProfile(
            user_id=profile.user_id,
            feature_weights=final_weights,
            learned_weights=learned_weights,
            stated_weights=profile.stated_weights,  # Keep original stated preferences
            confidence=confidence,
            high_importance_features=profile.high_importance_features,
            num_ratings=len(all_ratings)
        )
        
        logger.info(f"Updated profile: confidence {profile.confidence:.3f} → {confidence:.3f}")
        return updated_profile
    
    def explain_profile(self, profile: UserProfile) -> str:
        """
        Generate human-readable explanation of the user profile
        """
        explanations = []
        
        # Overall strategy
        if profile.confidence > 0.6:
            strategy = f"Primarily based on learned patterns from {profile.num_ratings} ratings"
        elif profile.confidence > 0.3:
            strategy = f"Balanced mix of stated preferences and learned patterns"
        else:
            strategy = "Based on stated importance scores"
        
        explanations.append(f"Profile Strategy: {strategy}")
        
        # Top features
        top_features = sorted(profile.feature_weights.items(), 
                            key=lambda x: x[1], reverse=True)[:5]
        
        explanations.append("\nTop Preferences:")
        for feature, weight in top_features:
            readable_name = feature.replace('_rate', '').replace('_', ' ').title()
            explanations.append(f"  {readable_name}: {weight:.3f}")
        
        # High importance constraints
        if profile.high_importance_features:
            constraint_names = [f.replace('_rate', '').replace('_', ' ').title() 
                              for f in profile.high_importance_features]
            explanations.append(f"\nHard Requirements: {', '.join(constraint_names)}")
        
        return "\n".join(explanations)


