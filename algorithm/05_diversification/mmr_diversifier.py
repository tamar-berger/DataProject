"""
Maximum Marginal Relevance (MMR) Diversification Module
Ensures diverse recommendations by balancing relevance and novelty
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Set
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)


class MMRDiversifier:
    """
    Implements Maximum Marginal Relevance (MMR) algorithm for diversifying recommendations.
    
    MMR Formula: MMR(c) = λ * Relevance(c) - (1-λ) * max[Similarity(c, r)] for r in selected
    
    This ensures we select countries that are both relevant and diverse from already selected ones.
    """
    
    def __init__(self,
                 lambda_param: float = 0.7,
                 similarity_metric: str = 'cosine',
                 feature_columns: Optional[List[str]] = None):
        """
        Initialize MMR diversifier
        
        Args:
            lambda_param: Trade-off between relevance and diversity (0-1)
                         1.0 = pure relevance, 0.0 = pure diversity
            similarity_metric: How to measure country similarity
            feature_columns: Specific features to use for similarity
        """
        self.lambda_param = lambda_param
        self.similarity_metric = similarity_metric
        self.feature_columns = feature_columns
        self.scaler = StandardScaler()
        
    def diversify_recommendations(self,
                                 candidate_scores: Dict[str, float],
                                 countries_df: pd.DataFrame,
                                 num_recommendations: int = 5) -> Tuple[List[Tuple[str, float]], Dict[str, any]]:
        """
        Apply MMR to select diverse set of recommendations
        
        Args:
            candidate_scores: Dictionary of country scores from scoring engine
            countries_df: DataFrame with country features for similarity calculation
            num_recommendations: Number of diverse recommendations to select
            
        Returns:
            Tuple of (selected_recommendations, diversification_info)
        """
        if not candidate_scores or num_recommendations <= 0:
            return [], {'strategy': 'none', 'diversity_lambda': self.lambda_param}
        
        diversification_info = {
            'strategy': 'mmr',
            'diversity_lambda': self.lambda_param,
            'initial_candidates': len(candidate_scores),
            'similarity_metric': self.similarity_metric
        }
        
        # Prepare feature matrix for similarity calculation
        feature_matrix, country_names = self._prepare_feature_matrix(countries_df, candidate_scores)
        
        if feature_matrix.size == 0:
            # Fallback to relevance-only selection
            logger.warning("No features available for diversity calculation, using relevance only")
            selected = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)[:num_recommendations]
            diversification_info['strategy'] = 'relevance_only'
            return selected, diversification_info
        
        # Apply MMR algorithm
        selected_countries = self._apply_mmr_algorithm(
            candidate_scores, feature_matrix, country_names, num_recommendations
        )
        
        # Calculate diversity metrics
        diversity_score = self._calculate_diversity_score(selected_countries, feature_matrix, country_names)
        diversification_info['diversity_score'] = diversity_score
        diversification_info['selected_count'] = len(selected_countries)
        
        logger.info(f"MMR diversification: selected {len(selected_countries)} countries "
                   f"with diversity score {diversity_score:.3f}")
        
        return selected_countries, diversification_info
    
    def _prepare_feature_matrix(self,
                               countries_df: pd.DataFrame,
                               candidate_scores: Dict[str, float]) -> Tuple[np.ndarray, List[str]]:
        """
        Prepare normalized feature matrix for countries in candidate set
        """
        # Filter to candidate countries only
        candidate_countries = set(candidate_scores.keys())
        filtered_df = countries_df[
            countries_df['country_name'].isin(candidate_countries)
        ].copy()
        
        if filtered_df.empty:
            return np.array([]), []
        
        # Determine feature columns
        if self.feature_columns:
            feature_cols = [col for col in self.feature_columns if col in filtered_df.columns]
        else:
            # Auto-detect feature columns
            feature_cols = [col for col in filtered_df.columns 
                           if col.endswith('_rate') or col.endswith('_index')]
        
        if not feature_cols:
            return np.array([]), []
        
        # Extract features and normalize
        feature_data = filtered_df[feature_cols].fillna(0)
        country_names = filtered_df['country_name'].tolist()
        
        # Normalize features for similarity calculation
        feature_matrix = self.scaler.fit_transform(feature_data.values)
        
        return feature_matrix, country_names
    
    def _apply_mmr_algorithm(self,
                            candidate_scores: Dict[str, float],
                            feature_matrix: np.ndarray,
                            country_names: List[str],
                            num_recommendations: int) -> List[Tuple[str, float]]:
        """
        Core MMR algorithm implementation
        """
        selected_countries = []
        selected_indices = []
        remaining_candidates = list(candidate_scores.keys())
        
        # Create mapping from country name to matrix index
        country_to_index = {name: i for i, name in enumerate(country_names) 
                           if name in candidate_scores}
        
        for selection_round in range(min(num_recommendations, len(remaining_candidates))):
            best_country = None
            best_mmr_score = -float('inf')
            best_index = -1
            
            # Evaluate each remaining candidate
            for country in remaining_candidates:
                if country not in country_to_index:
                    continue
                
                country_index = country_to_index[country]
                relevance_score = candidate_scores[country]
                
                # Calculate diversity penalty (similarity to already selected)
                diversity_penalty = 0.0
                if selected_indices:
                    similarities = self._calculate_similarities(
                        feature_matrix[country_index:country_index+1],
                        feature_matrix[selected_indices]
                    )
                    diversity_penalty = np.max(similarities)
                
                # MMR score
                mmr_score = (self.lambda_param * relevance_score - 
                            (1 - self.lambda_param) * diversity_penalty)
                
                if mmr_score > best_mmr_score:
                    best_mmr_score = mmr_score
                    best_country = country
                    best_index = country_index
            
            # Select the best country for this round
            if best_country:
                selected_countries.append((best_country, candidate_scores[best_country]))
                selected_indices.append(best_index)
                remaining_candidates.remove(best_country)
                
                logger.debug(f"MMR round {selection_round + 1}: selected {best_country} "
                           f"(MMR score: {best_mmr_score:.3f})")
        
        return selected_countries
    
    def _calculate_similarities(self,
                               query_features: np.ndarray,
                               reference_features: np.ndarray) -> np.ndarray:
        """
        Calculate similarities between query and reference features
        """
        if self.similarity_metric == 'cosine':
            similarities = cosine_similarity(query_features, reference_features).flatten()
        
        elif self.similarity_metric == 'euclidean':
            # Convert Euclidean distance to similarity
            distances = np.linalg.norm(query_features - reference_features, axis=1)
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            similarities = 1 - (distances / max_distance)
        
        elif self.similarity_metric == 'manhattan':
            # Convert Manhattan distance to similarity
            distances = np.sum(np.abs(query_features - reference_features), axis=1)
            max_distance = np.max(distances) if np.max(distances) > 0 else 1
            similarities = 1 - (distances / max_distance)
        
        else:
            # Fallback to cosine
            similarities = cosine_similarity(query_features, reference_features).flatten()
        
        return similarities
    
    def _calculate_diversity_score(self,
                                  selected_countries: List[Tuple[str, float]],
                                  feature_matrix: np.ndarray,
                                  country_names: List[str]) -> float:
        """
        Calculate overall diversity score of selected set
        """
        if len(selected_countries) < 2:
            return 1.0  # Perfect diversity for single item
        
        # Get feature vectors for selected countries
        selected_names = [country for country, _ in selected_countries]
        selected_indices = [i for i, name in enumerate(country_names) 
                           if name in selected_names]
        
        if len(selected_indices) < 2:
            return 1.0
        
        # Calculate pairwise similarities
        selected_features = feature_matrix[selected_indices]
        similarity_matrix = cosine_similarity(selected_features)
        
        # Average pairwise similarity (excluding diagonal)
        n = len(selected_indices)
        total_similarity = np.sum(similarity_matrix) - np.trace(similarity_matrix)
        avg_similarity = total_similarity / (n * (n - 1))
        
        # Diversity is inverse of similarity
        diversity_score = 1 - avg_similarity
        
        return max(0, min(1, diversity_score))
    
    def analyze_diversity(self,
                         recommendations: List[Tuple[str, float]],
                         countries_df: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze diversity characteristics of recommendations
        
        Returns:
            Dictionary with diversity analysis results
        """
        if len(recommendations) < 2:
            return {'diversity_analysis': 'insufficient_data'}
        
        country_names = [country for country, _ in recommendations]
        
        # Get country data
        country_data = countries_df[
            countries_df['country_name'].isin(country_names)
        ].copy()
        
        if len(country_data) < 2:
            return {'diversity_analysis': 'insufficient_data'}
        
        analysis = {
            'num_countries': len(country_names),
            'geographic_diversity': self._analyze_geographic_diversity(country_data),
            'feature_diversity': self._analyze_feature_diversity(country_data),
            'cluster_analysis': self._analyze_clustering(country_data)
        }
        
        return analysis
    
    def _analyze_geographic_diversity(self, country_data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze geographic diversity of recommendations
        """
        # This is a placeholder - you could add continent/region data to enhance this
        countries = country_data['country_name'].tolist()
        
        # Simple analysis based on country names (could be enhanced with actual geographic data)
        geographic_analysis = {
            'num_countries': len(countries),
            'countries': countries,
            'estimated_diversity': 'high' if len(countries) >= 5 else 'moderate'
        }
        
        return geographic_analysis
    
    def _analyze_feature_diversity(self, country_data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze diversity in feature values
        """
        feature_cols = [col for col in country_data.columns 
                       if col.endswith('_rate') or col.endswith('_index')]
        
        if not feature_cols:
            return {'analysis': 'no_features'}
        
        feature_diversity = {}
        
        for feature in feature_cols:
            values = country_data[feature].dropna()
            if len(values) > 1:
                # Coefficient of variation as diversity measure
                cv = values.std() / values.mean() if values.mean() != 0 else 0
                feature_diversity[feature] = {
                    'coefficient_of_variation': cv,
                    'range': (values.min(), values.max()),
                    'diversity_level': 'high' if cv > 0.2 else 'moderate' if cv > 0.1 else 'low'
                }
        
        return feature_diversity
    
    def _analyze_clustering(self, country_data: pd.DataFrame) -> Dict[str, any]:
        """
        Analyze how countries cluster together
        """
        feature_cols = [col for col in country_data.columns 
                       if col.endswith('_rate') or col.endswith('_index')]
        
        if not feature_cols or len(country_data) < 3:
            return {'analysis': 'insufficient_data'}
        
        # Simple clustering analysis using pairwise distances
        features = country_data[feature_cols].fillna(0)
        normalized_features = self.scaler.fit_transform(features.values)
        
        # Calculate average pairwise distance
        distances = []
        for i in range(len(normalized_features)):
            for j in range(i + 1, len(normalized_features)):
                dist = np.linalg.norm(normalized_features[i] - normalized_features[j])
                distances.append(dist)
        
        avg_distance = np.mean(distances) if distances else 0
        
        clustering_analysis = {
            'average_pairwise_distance': avg_distance,
            'clustering_tendency': 'diverse' if avg_distance > 1.5 else 'clustered',
            'num_distances_calculated': len(distances)
        }
        
        return clustering_analysis


