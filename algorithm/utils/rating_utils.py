"""
Rating normalization utilities for the Smart Country Recommender System

Handles conversion between 1-5 star ratings and 0.2-1.0 normalized scale
"""

from typing import Dict, Union


def normalize_rating(rating: Union[int, float]) -> float:
    """
    Normalize a 1-5 star rating to 0.2-1.0 scale
    
    Args:
        rating: Rating in 1-5 scale
        
    Returns:
        Normalized rating in 0.2-1.0 scale
        
    Examples:
        1 star -> 0.2
        2 stars -> 0.4  
        3 stars -> 0.6
        4 stars -> 0.8
        5 stars -> 1.0
    """
    if rating < 1 or rating > 5:
        raise ValueError(f"Rating must be between 1-5, got {rating}")
    
    return rating * 0.2


def denormalize_rating(normalized_rating: float) -> float:
    """
    Convert normalized rating (0.2-1.0) back to 1-5 star scale
    
    Args:
        normalized_rating: Rating in 0.2-1.0 scale
        
    Returns:
        Rating in 1-5 star scale
        
    Examples:
        0.2 -> 1 star
        0.4 -> 2 stars
        0.6 -> 3 stars
        0.8 -> 4 stars
        1.0 -> 5 stars
    """
    if normalized_rating < 0.2 or normalized_rating > 1.0:
        raise ValueError(f"Normalized rating must be between 0.2-1.0, got {normalized_rating}")
    
    return normalized_rating / 0.2


def normalize_ratings_dict(ratings: Dict[str, Union[int, float]]) -> Dict[str, float]:
    """
    Normalize a dictionary of ratings from 1-5 scale to 0.2-1.0 scale
    
    Args:
        ratings: Dictionary mapping items to 1-5 star ratings
        
    Returns:
        Dictionary mapping items to normalized ratings (0.2-1.0)
    """
    return {item: normalize_rating(rating) for item, rating in ratings.items()}


def get_rating_threshold(stars: Union[int, float]) -> float:
    """
    Convert star threshold to normalized threshold
    
    Args:
        stars: Star threshold (e.g., 3.5 for "3.5 stars or above")
        
    Returns:
        Normalized threshold
        
    Examples:
        3 stars -> 0.6 normalized
        3.5 stars -> 0.7 normalized
        4 stars -> 0.8 normalized
    """
    if stars < 1 or stars > 5:
        raise ValueError(f"Star threshold must be between 1-5, got {stars}")
    
    return stars * 0.2


def is_rating_positive(rating: Union[int, float], threshold_stars: float = 3.5) -> bool:
    """
    Check if a rating is considered positive (above threshold)
    
    Args:
        rating: Rating in 1-5 scale
        threshold_stars: Minimum stars to consider positive
        
    Returns:
        True if rating is above threshold
    """
    return rating >= threshold_stars


def is_normalized_rating_positive(normalized_rating: float, threshold_stars: float = 3.5) -> bool:
    """
    Check if a normalized rating is considered positive
    
    Args:
        normalized_rating: Rating in 0.2-1.0 scale
        threshold_stars: Minimum stars to consider positive (will be normalized)
        
    Returns:
        True if rating is above threshold
    """
    normalized_threshold = get_rating_threshold(threshold_stars)
    return normalized_rating >= normalized_threshold


# Constants for common thresholds
RATING_THRESHOLD_LIKED = get_rating_threshold(3.5)  # 0.7 - Countries user likes
RATING_THRESHOLD_NEUTRAL = get_rating_threshold(3.0)  # 0.6 - Neutral threshold
RATING_THRESHOLD_DISLIKED = get_rating_threshold(2.5)  # 0.5 - Below this is disliked

# Rating scale bounds
MIN_RATING = 1
MAX_RATING = 5
MIN_NORMALIZED_RATING = 0.2
MAX_NORMALIZED_RATING = 1.0