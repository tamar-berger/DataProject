"""
Similarity-Based Scoring Module
Scores countries based on similarity to user's previously liked countries
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class SimilarityBasedScorer:
    """
    Scores countries based on similarity to user's liked countries.
    
    Uses cosine similarity between country feature vectors.
    """
    
    def __init__(self, 
                 similarity_metric: str = 'cosine',
                 rating_threshold: float = 0.6, 
                 feature_columns: Optional[List[str]] = None):
        """
        Initialize similarity scorer
        
        Args:
            similarity_metric: Similarity measure ('cosine', 'euclidean', 'manhattan')
            rating_threshold: Minimum normalized rating to consider a country "liked" (0.2-1.0 scale)
            feature_columns: Specific features to use for similarity
        """
        self.similarity_metric = similarity_metric
        self.rating_threshold = rating_threshold
        self.feature_columns = feature_columns
        self.scaler = StandardScaler()
        
    def score_countries(self,
                       countries_df: pd.DataFrame,
                       user_ratings: Dict[str, float],
                       target_countries: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Score countries based on similarity to user's liked countries
        
        Args:
            countries_df: DataFrame with all country features
            user_ratings: Dictionary of user ratings {country_name: rating} (1-5 scale, will be normalized)
            target_countries: Countries to score (if None, score all)
            
        Returns:
            Dictionary mapping country names to similarity scores (0-1)
        """
        if not user_ratings or countries_df.empty:
            return {}
        
        # Normalize ratings from 1-5 scale to 0.2-1.0 scale and get liked countries
        normalized_ratings = {country: rating * 0.2 for country, rating in user_ratings.items()}
        liked_countries = [country for country, rating in normalized_ratings.items() 
                          if rating >= self.rating_threshold]
        
        if not liked_countries:
            logger.warning(f"No liked countries found above threshold {self.rating_threshold}")
            return {}
        
        # Prepare feature matrix
        feature_matrix, country_names = self._prepare_feature_matrix(countries_df)
        
        if feature_matrix.size == 0:
            return {}
        
        # Get indices of liked countries
        liked_indices = []
        for country in liked_countries:
            if country in country_names:
                liked_indices.append(country_names.index(country))
        
        if not liked_indices:
            logger.warning("No liked countries found in feature data")
            return {}
        
        # Calculate similarity scores
        scores = self._calculate_similarity_scores(
            feature_matrix, liked_indices, country_names, target_countries
        )
        
        logger.info(f"Calculated similarity scores for {len(scores)} countries "
                   f"based on {len(liked_indices)} liked countries")
        return scores
    
    def _prepare_feature_matrix(self, countries_df: pd.DataFrame) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare normalized feature matrix for similarity calculation
        """
        # Determine feature columns
        if self.feature_columns:
            feature_cols = [col for col in self.feature_columns if col in countries_df.columns]
        else:
            # Auto-detect numeric feature columns
            feature_cols = [col for col in countries_df.columns 
                           if col.endswith('_rate') or col.endswith('_index')]
        
        if not feature_cols:
            logger.warning("No feature columns found for similarity calculation")
            return np.array([]), []
        
        # Extract features and country names
        feature_data = countries_df[feature_cols].fillna(0)  # Fill NaN with 0
        country_names = countries_df.get('country_name', countries_df.get('country', [])).tolist()
        
        # Normalize features
        feature_matrix = self.scaler.fit_transform(feature_data.values)
        
        return feature_matrix, country_names
    
    def _calculate_similarity_scores(self,
                                   feature_matrix: np.ndarray,
                                   liked_indices: List[int],
                                   country_names: List[str],
                                   target_countries: Optional[List[str]]) -> Dict[str, float]:
        """
        Calculate similarity scores using specified metric
        """
        scores = {}
        
        # Get feature vectors for liked countries
        liked_vectors = feature_matrix[liked_indices]
        
        # Calculate prototype vector (centroid of liked countries)
        if len(liked_vectors) > 1:
            prototype_vector = np.mean(liked_vectors, axis=0).reshape(1, -1)
        else:
            prototype_vector = liked_vectors
        
        # Calculate similarities
        if self.similarity_metric == 'cosine':
            similarities = cosine_similarity(feature_matrix, prototype_vector).flatten()
        
        elif self.similarity_metric == 'euclidean':
            # Convert distance to similarity (higher = more similar)
            distances = np.linalg.norm(feature_matrix - prototype_vector, axis=1)
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            similarities = 1 - (distances / max_distance)
        
        elif self.similarity_metric == 'manhattan':
            # Manhattan distance converted to similarity
            distances = np.sum(np.abs(feature_matrix - prototype_vector), axis=1)
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            similarities = 1 - (distances / max_distance)
        
        else:
            logger.error(f"Unknown similarity metric: {self.similarity_metric}")
            return {}
        
        # Convert to dictionary, filtering by target countries if specified
        for i, country_name in enumerate(country_names):
            if target_countries is None or country_name in target_countries:
                # Ensure score is in 0-1 range
                score = max(0, min(1, similarities[i]))
                scores[country_name] = score
        
        return scores
    
    def get_most_similar_countries(self,
                                  countries_df: pd.DataFrame,
                                  reference_country: str,
                                  top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find countries most similar to a reference country
        
        Args:
            countries_df: DataFrame with country features
            reference_country: Country to find similar countries for
            top_k: Number of similar countries to return
            
        Returns:
            List of (country_name, similarity_score) tuples
        """
        # Fake a high rating for the reference country (5 stars)
        fake_ratings = {reference_country: 5.0}
        
        # Get similarity scores
        scores = self.score_countries(countries_df, fake_ratings)
        
        # Remove the reference country itself
        scores.pop(reference_country, None)
        
        # Return top K most similar
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:top_k]
    
    def explain_similarity(self,
                          countries_df: pd.DataFrame,
                          target_country: str,
                          reference_countries: List[str]) -> Dict[str, float]:
        """
        Explain what makes countries similar (feature-level analysis)
        
        Returns:
            Dictionary with feature similarity contributions
        """
        # Prepare feature data
        feature_matrix, country_names = self._prepare_feature_matrix(countries_df)
        
        if target_country not in country_names:
            return {}
        
        target_idx = country_names.index(target_country)
        target_vector = feature_matrix[target_idx]
        
        # Get reference vectors
        reference_indices = [country_names.index(c) for c in reference_countries 
                           if c in country_names]
        
        if not reference_indices:
            return {}
        
        reference_vectors = feature_matrix[reference_indices]
        prototype_vector = np.mean(reference_vectors, axis=0)
        
        # Feature columns
        feature_cols = [col for col in countries_df.columns 
                       if col.endswith('_rate') or col.endswith('_index')]
        
        # Calculate feature-wise similarities
        feature_similarities = {}
        for i, feature in enumerate(feature_cols):
            # Cosine similarity for individual features
            target_val = target_vector[i]
            prototype_val = prototype_vector[i]
            
            # Simple similarity measure
            if abs(target_val) < 1e-10 and abs(prototype_val) < 1e-10:
                similarity = 1.0  # Both zero
            else:
                # Normalized difference
                max_val = max(abs(target_val), abs(prototype_val))
                similarity = 1 - abs(target_val - prototype_val) / (max_val + 1e-10)
            
            feature_similarities[feature] = max(0, similarity)
        
        return feature_similarities


