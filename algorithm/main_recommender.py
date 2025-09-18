"""
Main Smart Country Recommender System
Orchestrates the complete recommendation pipeline
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging
from pathlib import Path

from config import DATABASE_PATH, HYPERPARAMETERS, FEATURES, PREFERENCE_MAPPING

# Import algorithm modules
import importlib
import sys
from pathlib import Path

# Add algorithm directory to path for numbered module imports
algo_path = Path(__file__).parent
sys.path.insert(0, str(algo_path))

# Import from numbered directories
feature_engineering = importlib.import_module('01_feature_engineering.feature_processor')
data_validation = importlib.import_module('01_feature_engineering.data_validator')
user_modeling = importlib.import_module('02_user_modeling.profile_builder')
scoring_engine = importlib.import_module('03_scoring_engine.hybrid_scorer')
constraint_filtering = importlib.import_module('04_constraint_filtering.constraint_filter')
diversification = importlib.import_module('05_diversification.mmr_diversifier')

FeatureProcessor = feature_engineering.FeatureProcessor
DataValidator = data_validation.DataValidator
UserProfileBuilder = user_modeling.UserProfileBuilder
HybridScorer = scoring_engine.HybridScorer
ConstraintFilter = constraint_filtering.ConstraintFilter
MMRDiversifier = diversification.MMRDiversifier

logger = logging.getLogger(__name__)


@dataclass
class UserPreferences:
    """Anonymous user preference data structure"""
    importance_scores: Dict[str, int]  # e.g., {'Safety level': 85, 'English speaking level': 70} (0-100 scale)
    country_ratings: Dict[str, float] = None  # country_name -> rating (1-5 stars)


@dataclass
class RecommendationResult:
    """Recommendation result data structure"""
    countries: List[str]
    scores: List[float]
    explanations: List[str]
    user_profile: Dict[str, float]
    algorithm_version: str
    timestamp: str


class SmartCountryRecommender:
    """
    Main recommendation system that orchestrates all algorithm components
    """
    
    def __init__(self, database_path: str = DATABASE_PATH):
        """
        Initialize the recommender system
        
        Args:
            database_path: Path to the SQLite database
        """
        self.database_path = database_path
        self.hyperparams = HYPERPARAMETERS
        
        # Initialize preprocessing components
        self.data_validator = DataValidator(strict_mode=False, auto_fix=True)
        self.feature_processor = FeatureProcessor(
            normalization_method='none',  # Data already normalized 0-1 in database
            imputation_strategy='median',
            outlier_method='iqr',
            feature_selection=False
        )
        
        # Initialize algorithm components
        self.profile_builder = UserProfileBuilder(PREFERENCE_MAPPING)
        self.hybrid_scorer = HybridScorer()
        self.constraint_filter = ConstraintFilter(
            high_importance_threshold=self.hyperparams['high_importance_threshold']
        )
        self.diversifier = MMRDiversifier()
        
        # Configuration for ablation studies
        self.ablation_config = {
            'use_preprocessing': True,
            'use_similarity': True,
            'use_mmr': True,
            'use_constraints': True
        }
        
        # Cache for processed data
        self._processed_data_cache = None
        self._processing_metadata = None
        
        logger.info("SmartCountryRecommender initialized with complete pipeline")
    
    def load_country_data(self) -> pd.DataFrame:
        """
        Load and return preprocessed country data from database
        
        Returns:
            DataFrame with validated and processed country features
        """
        # Check cache first
        if self._processed_data_cache is not None and self.ablation_config.get('use_preprocessing', True):
            logger.info("Using cached processed data")
            return self._processed_data_cache
        
        # Load raw data
        conn = sqlite3.connect(self.database_path)
        query = "SELECT * FROM country_indicators"
        raw_df = pd.read_sql_query(query, conn)
        conn.close()
        
        logger.info(f"Loaded {len(raw_df)} countries from database")
        
        # Apply preprocessing pipeline if enabled
        if self.ablation_config.get('use_preprocessing', True):
            processed_df = self._preprocess_data(raw_df)
        else:
            processed_df = raw_df
            logger.info("Preprocessing disabled - using raw data")
        
        return processed_df
    
    def _preprocess_data(self, raw_df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply complete preprocessing pipeline to raw data
        
        Args:
            raw_df: Raw country data from database
            
        Returns:
            Processed and validated DataFrame
        """
        logger.info("Starting data preprocessing pipeline")
        
        # Step 1: Data validation and cleaning
        is_valid, validation_report, validated_df = self.data_validator.validate_data(raw_df)
        
        if not is_valid and validated_df is None:
            logger.warning("Data validation failed and no fixes available")
            validated_df = raw_df
        elif validated_df is not None:
            logger.info(f"Data validation: {validation_report['overall_status']}")
            if validation_report.get('fixes_applied'):
                logger.info(f"Applied {len(validation_report['fixes_applied'])} data fixes")
        
        # Step 2: Feature processing
        processed_df, processing_metadata = self.feature_processor.process_features(validated_df)
        
        # Cache the results
        self._processed_data_cache = processed_df
        self._processing_metadata = {
            'validation_report': validation_report,
            'processing_metadata': processing_metadata
        }
        
        logger.info(f"Preprocessing complete: {processed_df.shape[0]} countries, "
                   f"{len(processing_metadata['feature_names'])} features")
        
        return processed_df
    
    def get_preprocessing_report(self) -> Dict[str, Any]:
        """
        Get detailed report of preprocessing steps applied
        
        Returns:
            Dictionary with validation and processing details
        """
        if self._processing_metadata is None:
            return {'status': 'no_preprocessing_performed'}
        
        return self._processing_metadata
    
    def recommend(self, 
                 user_preferences: UserPreferences,
                 num_recommendations: int = 5) -> RecommendationResult:
        """
        Generate country recommendations for anonymous user
        
        Args:
            user_preferences: Anonymous user preference data (0-100 importance scores)
            num_recommendations: Number of countries to recommend
            
        Returns:
            RecommendationResult with countries and scores
        """
        logger.info(f"Generating {num_recommendations} anonymous recommendations")
        
        # Step 1: Load country data
        countries_df = self.load_country_data()
        
        # Step 2: Build user profile from preferences and ratings
        user_profile = self.profile_builder.build_profile(
            user_id="anonymous",
            importance_scores=user_preferences.importance_scores,
            user_ratings=user_preferences.country_ratings,
            country_features=countries_df
        )
        
        # Step 3: Score all countries using hybrid approach
        scores, scoring_info = self.hybrid_scorer.score_countries(
            countries_df=countries_df,
            user_weights=user_profile.feature_weights,
            user_ratings=user_preferences.country_ratings,
            user_confidence=user_profile.confidence
        )
        
        # Step 4: Apply constraint filtering (if enabled)
        if self.ablation_config['use_constraints']:
            filtered_df, constraint_info = self.constraint_filter.apply_constraints(
                countries_df=countries_df,
                importance_scores=user_preferences.importance_scores,
                preference_mapping=PREFERENCE_MAPPING,
                scores=scores
            )
            
            # Filter scores to match filtered countries
            filtered_scores = {country: score for country, score in scores.items()
                              if country in filtered_df['country_name'].values}
        else:
            filtered_scores = scores
            constraint_info = {'applied_constraints': [], 'relaxed_constraints': []}
        
        # Step 5: Diversify recommendations (if enabled)
        if self.ablation_config['use_mmr'] and len(filtered_scores) > num_recommendations:
            diverse_recommendations, diversity_info = self.diversifier.diversify_recommendations(
                candidate_scores=filtered_scores,
                countries_df=countries_df,
                num_recommendations=num_recommendations
            )
        else:
            # Just take top scores
            sorted_scores = sorted(filtered_scores.items(), key=lambda x: x[1], reverse=True)
            diverse_recommendations = sorted_scores[:num_recommendations]
            diversity_info = {'strategy': 'relevance_only'}
        
        # Skip explanation generation - just return recommendations
        
        return RecommendationResult(
            countries=[country for country, _ in diverse_recommendations],
            scores=[score for _, score in diverse_recommendations],
            explanations=[],  # No explanations
            user_profile=user_profile.feature_weights,
            algorithm_version="streamlined_v1",
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def recommend_countries(self,
                           importance_scores: Dict[str, int],
                           user_ratings: Optional[Dict[str, float]] = None,
                           num_recommendations: int = 5) -> Tuple[List[Tuple[str, float]], Dict[str, any]]:
        """
        API method for generating anonymous country recommendations
        
        Args:
            importance_scores: User importance ratings (0-100 scale) for categories:
                - 'Safety level'
                - 'English speaking level' 
                - 'Health care quality'
                - 'Budget friendliness'
                - 'Public transport access'
                - 'Culture accessibility rate'
                - 'Nature and scenery'
                - 'Tourism crowd level'
            user_ratings: Optional country ratings (1-5 stars) from countries user has visited
            num_recommendations: Number of recommendations to return
            
        Returns:
            Tuple of (recommendations, explanation_data)
            recommendations: List of (country_name, score) tuples
            explanation_data: Dict with algorithm metadata
        """
        user_prefs = UserPreferences(
            importance_scores=importance_scores,
            country_ratings=user_ratings
        )
        
        result = self.recommend(user_prefs, num_recommendations)
        
        recommendations = [(country, score) for country, score in zip(result.countries, result.scores)]
        explanation_data = {
            'algorithm_version': result.algorithm_version,
            'user_profile': result.user_profile,
            'num_countries_scored': len(result.countries)
        }
        
        return recommendations, explanation_data
    
    def configure_ablation_mode(self, config: Dict[str, bool]) -> None:
        """
        Configure ablation study settings
        
        Args:
            config: Dictionary with component enablement flags
        """
        self.ablation_config.update(config)
        logger.info(f"Ablation config updated: {self.ablation_config}")
    
    def _placeholder_recommend(self, 
                              countries_df: pd.DataFrame,
                              user_prefs: UserPreferences, 
                              num_recs: int) -> RecommendationResult:
        """
        Placeholder recommendation logic until full implementation
        """
        # Simple weighted scoring based on user importance
        weights = {}
        for pref_name, importance in user_prefs.importance_scores.items():
            if pref_name in PREFERENCE_MAPPING:
                for feature in PREFERENCE_MAPPING[pref_name]:
                    weights[feature] = weights.get(feature, 0) + importance / 10.0
        
        # Calculate weighted scores
        scores = []
        for _, country in countries_df.iterrows():
            score = 0
            for feature, weight in weights.items():
                if feature in countries_df.columns:
                    score += country[feature] * weight
            scores.append(score)
        
        # Get top recommendations
        countries_df['score'] = scores
        top_countries = countries_df.nlargest(num_recs, 'score')
        
        # Generate simple explanations
        explanations = []
        for _, country in top_countries.iterrows():
            top_features = []
            for pref_name, importance in user_prefs.importance_scores.items():
                if importance >= 8:  # High importance
                    top_features.append(pref_name.lower())
            
            explanation = f"Good match for your priorities: {', '.join(top_features)}"
            explanations.append(explanation)
        
        return RecommendationResult(
            countries=top_countries['country_name'].tolist(),
            scores=top_countries['score'].tolist(),
            explanations=explanations,
            user_profile=weights,
            algorithm_version="placeholder_v1",
            timestamp=pd.Timestamp.now().isoformat()
        )
    
    def evaluate(self, 
                test_users: List[UserPreferences],
                metrics: List[str] = ['mae', 'precision_at_5']) -> Dict[str, float]:
        """
        Evaluate the recommendation system using test users
        
        Args:
            test_users: List of users with known ratings for evaluation
            metrics: List of metrics to compute
            
        Returns:
            Dictionary of metric names to values
        """
        # return self.offline_evaluator.evaluate(test_users, metrics)
        
        # Placeholder
        return {'mae': 0.8, 'precision_at_5': 0.6}

