"""
Hybrid Scoring Module
Combines content-based and similarity-based scoring with intelligent weighting
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging

try:
    from .content_scorer import ContentBasedScorer
    from .similarity_scorer import SimilarityBasedScorer
except ImportError:
    # Handle direct imports when not using package structure
    from content_scorer import ContentBasedScorer
    from similarity_scorer import SimilarityBasedScorer

logger = logging.getLogger(__name__)


class HybridScorer:
    """
    Intelligent hybrid scorer that adaptively combines content-based and similarity-based approaches.
    
    Key innovation: Dynamically adjusts weighting based on data availability and user history.
    """
    
    def __init__(self, 
                 content_weight: float = 0.3,
                 similarity_weight: float = 0.7,
                 min_ratings_for_similarity: int = 3,
                 confidence_threshold: float = 0.3):
        """
        Initialize hybrid scorer
        
        Args:
            content_weight: Base weight for content-based scoring
            similarity_weight: Base weight for similarity-based scoring
            min_ratings_for_similarity: Minimum ratings needed for similarity scoring
            confidence_threshold: Minimum confidence to use learned preferences
        """
        self.base_content_weight = content_weight
        self.base_similarity_weight = similarity_weight
        self.min_ratings_for_similarity = min_ratings_for_similarity
        self.confidence_threshold = confidence_threshold
        
        # Initialize component scorers
        self.content_scorer = ContentBasedScorer(score_scaling='linear')
        self.similarity_scorer = SimilarityBasedScorer(similarity_metric='cosine')
        
    def score_countries(self,
                       countries_df: pd.DataFrame,
                       user_weights: Dict[str, float],
                       user_ratings: Optional[Dict[str, float]] = None,
                       user_confidence: float = 0.0) -> Tuple[Dict[str, float], Dict[str, any]]:
        """
        Score countries using hybrid approach
        
        Args:
            countries_df: DataFrame with country features
            user_weights: User preference weights from profile
            user_ratings: Optional historical ratings for similarity (1-5 scale, will be normalized)
            user_confidence: Confidence in learned preferences (0-1)
            
        Returns:
            Tuple of (final_scores, explanation_data)
        """
        explanation_data = {
            'strategy': 'content_only',
            'content_weight': 1.0,
            'similarity_weight': 0.0,
            'num_ratings': len(user_ratings) if user_ratings else 0
        }
        
        # Always get content-based scores
        content_scores = self.content_scorer.score_countries(countries_df, user_weights)
        
        if not content_scores:
            logger.warning("No content scores generated")
            return {}, explanation_data
        
        # Determine if we can use similarity scoring
        use_similarity = (user_ratings and 
                         len(user_ratings) >= self.min_ratings_for_similarity and
                         user_confidence >= self.confidence_threshold)
        
        if not use_similarity:
            logger.info(f"Using content-only scoring (ratings: {len(user_ratings) if user_ratings else 0}, "
                       f"confidence: {user_confidence:.3f})")
            return content_scores, explanation_data
        
        # Get similarity scores
        similarity_scores = self.similarity_scorer.score_countries(countries_df, user_ratings)
        
        if not similarity_scores:
            logger.warning("Similarity scoring failed, falling back to content-only")
            return content_scores, explanation_data
        
        # Calculate adaptive weights
        content_weight, similarity_weight = self._calculate_adaptive_weights(
            user_confidence, len(user_ratings), content_scores, similarity_scores
        )
        
        # Combine scores
        final_scores = self._combine_scores(content_scores, similarity_scores, 
                                          content_weight, similarity_weight)
        
        explanation_data.update({
            'strategy': 'hybrid',
            'content_weight': content_weight,
            'similarity_weight': similarity_weight,
            'user_confidence': user_confidence
        })
        
        logger.info(f"Hybrid scoring: {content_weight:.3f} content + {similarity_weight:.3f} similarity")
        return final_scores, explanation_data
    
    def _calculate_adaptive_weights(self,
                                  user_confidence: float,
                                  num_ratings: int,
                                  content_scores: Dict[str, float],
                                  similarity_scores: Dict[str, float]) -> Tuple[float, float]:
        """
        Calculate adaptive weights based on data quality and user history
        """
        # Base weights
        content_weight = self.base_content_weight
        similarity_weight = self.base_similarity_weight
        
        # Adjust based on confidence in learned preferences
        if user_confidence > 0.7:
            # High confidence: trust content-based more
            content_weight = min(0.8, content_weight + 0.1)
        elif user_confidence < 0.4:
            # Low confidence: rely more on similarity
            similarity_weight = min(0.7, similarity_weight + 0.2)
        
        # Adjust based on rating history richness
        rating_factor = min(1.0, num_ratings / 10.0)  # Normalize by 10 ratings
        similarity_weight = similarity_weight * rating_factor
        
        # Adjust based on score quality/variance
        content_variance = np.var(list(content_scores.values()))
        similarity_variance = np.var(list(similarity_scores.values()))
        
        # If one approach has much higher variance (discrimination), weight it more
        if content_variance > 1.5 * similarity_variance:
            content_weight += 0.1
        elif similarity_variance > 1.5 * content_variance:
            similarity_weight += 0.1
        
        # Normalize weights to sum to 1
        total_weight = content_weight + similarity_weight
        if total_weight > 0:
            content_weight /= total_weight
            similarity_weight /= total_weight
        
        return content_weight, similarity_weight
    
    def _combine_scores(self,
                       content_scores: Dict[str, float],
                       similarity_scores: Dict[str, float],
                       content_weight: float,
                       similarity_weight: float) -> Dict[str, float]:
        """
        Combine content and similarity scores using weighted average
        """
        all_countries = set(content_scores.keys()) | set(similarity_scores.keys())
        combined_scores = {}
        
        for country in all_countries:
            content_score = content_scores.get(country, 0.0)
            similarity_score = similarity_scores.get(country, 0.0)
            
            # Weighted combination
            combined_score = (content_weight * content_score + 
                            similarity_weight * similarity_score)
            
            combined_scores[country] = combined_score
        
        return combined_scores
    
    def explain_country_score(self,
                             country_name: str,
                             countries_df: pd.DataFrame,
                             user_weights: Dict[str, float],
                             user_ratings: Optional[Dict[str, float]] = None) -> Dict[str, any]:
        """
        Provide detailed explanation of how a country's score was calculated
        
        Returns:
            Dictionary with score breakdown and explanations
        """
        explanation = {
            'country': country_name,
            'content_breakdown': {},
            'similarity_info': {},
            'final_strategy': 'content_only'
        }
        
        # Get country data
        country_row = countries_df[countries_df['country_name'] == country_name]
        if country_row.empty:
            return explanation
        
        country_data = country_row.iloc[0]
        
        # Content-based explanation
        content_contributions = self.content_scorer.explain_score(
            country_name, country_data, user_weights
        )
        explanation['content_breakdown'] = content_contributions
        
        # Similarity-based explanation (if applicable)
        if (user_ratings and len(user_ratings) >= self.min_ratings_for_similarity):
            liked_countries = [c for c, r in user_ratings.items() if r >= 3.5]
            
            if liked_countries:
                similarity_features = self.similarity_scorer.explain_similarity(
                    countries_df, country_name, liked_countries
                )
                explanation['similarity_info'] = {
                    'liked_countries': liked_countries,
                    'feature_similarities': similarity_features
                }
                explanation['final_strategy'] = 'hybrid'
        
        return explanation
    
    def get_score_confidence(self,
                           final_scores: Dict[str, float],
                           explanation_data: Dict[str, any]) -> float:
        """
        Calculate confidence in the scoring results
        
        Returns:
            Confidence score (0-1) based on data quality and score distribution
        """
        if not final_scores:
            return 0.0
        
        scores = list(final_scores.values())
        
        # Base confidence from strategy
        if explanation_data['strategy'] == 'hybrid':
            base_confidence = 0.8
        else:
            base_confidence = 0.6
        
        # Adjust based on score variance (higher variance = better discrimination)
        score_variance = np.var(scores)
        variance_factor = min(1.0, score_variance * 4)  # Scale variance
        
        # Adjust based on number of ratings (for similarity component)
        rating_factor = 1.0
        if explanation_data['num_ratings'] > 0:
            rating_factor = min(1.0, explanation_data['num_ratings'] / 8.0)
        
        # Adjust based on user confidence (if available)
        user_confidence_factor = explanation_data.get('user_confidence', 0.5)
        
        # Combined confidence
        confidence = base_confidence * variance_factor * rating_factor * user_confidence_factor
        
        return max(0.1, min(1.0, confidence))


