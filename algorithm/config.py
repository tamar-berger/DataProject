"""
Configuration file for Smart Country Recommender Algorithm
Contains hyperparameters, database settings, and feature mappings
"""

import os
from pathlib import Path

# Database Configuration  
DATABASE_PATH = Path(__file__).parent.parent / "country_rates.db"

# Feature Configuration
FEATURES = {
    'safety': 'safety_rate',
    'crime': 'crime_rate', 
    'english': 'english_score_rate',
    'health': 'health_care_rate',
    'budget': 'cost_of_living_rate',  # Note: already inverted (higher = more affordable)
    'culture': 'cultural_accessibility_rate',
    'transport': 'public_transport_rate',
    'tourism': 'tourism_arrivals_rate',
    'nature': 'natural_spaces_rate'
}

# User Preference Mapping
# Maps user importance categories to database features
PREFERENCE_MAPPING = {
    'Budget friendliness': ['cost_of_living_rate'],
    'Safety level': ['safety_rate', 'crime_rate'],
    'English speaking level': ['english_score_rate'],
    'Public transport access': ['public_transport_rate'],
    'Health care quality': ['health_care_rate'],
    'Culture accessibility rate': ['cultural_accessibility_rate'],
    'Nature and scenery': ['natural_spaces_rate'],
    'Tourism crowd level': ['tourism_arrivals_rate']
}

# Algorithm Hyperparameters
HYPERPARAMETERS = {
    # User Modeling
    'learning_rate_decay': 0.1,  # How much to weight each additional rating
    'min_ratings_for_learned': 3,  # Minimum ratings to trust learned preferences
    'max_learned_weight': 0.8,  # Maximum weight for learned vs stated preferences
    
    # Scoring
    'content_weight': 0.6,  # Weight for content-based scoring
    'neighborhood_weight': 0.3,  # Weight for neighborhood-based scoring  
    'popularity_weight': 0.1,  # Weight for popularity scoring
    'similarity_threshold': 0.7,  # Minimum similarity for neighborhood effect
    
    # Constraints  
    'high_importance_threshold': 80,  # Importance level that triggers constraints (0-100 scale)
    'constraint_percentiles': {  # Required percentile for high importance features
        80: 50,   # Importance 80 → top 50%
        90: 25,   # Importance 90 → top 25%  
        100: 10   # Importance 100 → top 10%
    },
    'min_countries_after_filtering': 10,  # Minimum countries after constraint filtering
    
    # Diversification  
    'diversity_lambda': 0.7,  # MMR lambda parameter (relevance vs diversity)
    'min_diversity_distance': 0.3,  # Minimum feature distance between recommendations
    'clustering_k': 5,  # Number of clusters for clustering-based diversity
    
    # Evaluation
    'cv_folds': 5,  # Cross-validation folds
    'test_split': 0.2,  # Train/test split ratio
    'random_state': 42,  # For reproducibility
}

# Explanation Templates
EXPLANATION_TEMPLATES = {
    'high_match': "Excellent {feature} ({percentile}th percentile) matches your high {preference} priority.",
    'good_match': "Strong {feature} ({percentile}th percentile) aligns with your {preference} preference.", 
    'acceptable': "{feature} is acceptable (average level) for your needs.",
    'trade_off': "{feature} is below average, but other strengths compensate.",
    'constraint_met': "Meets your required {preference} standards.",
    'diversity_pick': "Offers different experiences while meeting your core preferences."
}

# Visualization Configuration
VIZ_CONFIG = {
    'recommendation_plot_size': (12, 8),
    'feature_importance_colors': ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd'],
    'map_style': 'carto-positron',  # For plotly maps
    'default_font_size': 12
}

# API Configuration (if building web service)
API_CONFIG = {
    'host': '0.0.0.0',
    'port': 8000,
    'debug': True,
    'max_recommendations': 20,
    'default_recommendations': 5,
    'cache_ttl': 3600  # Cache TTL in seconds
}