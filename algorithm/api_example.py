#!/usr/bin/env python3
"""
API Example for Smart Country Recommender System

This demonstrates the corrected API format with:
- 0-100 importance scores
- No user ID (anonymous recommendations)
- 1-5 star country ratings for visited countries
"""

import os
import sys
from pathlib import Path

# Add algorithm directory to path
algorithm_dir = Path(__file__).parent
sys.path.insert(0, str(algorithm_dir))

from main_recommender import SmartCountryRecommender


def api_example_1():
    """
    Example 1: New user with no travel history, only preferences
    """
    print("🌍 API Example 1: New User (Safety-focused)")
    print("=" * 50)
    
    # Initialize recommender
    recommender = SmartCountryRecommender()
    
    # API call parameters
    importance_scores = {
        'Safety level': 95,              # Very high priority
        'English speaking level': 85,    # High priority  
        'Health care quality': 80,       # High priority
        'Budget friendliness': 60,       # Medium priority
        'Public transport access': 50,   # Medium priority
        'Culture accessibility rate': 40, # Lower priority
        'Nature and scenery': 30,        # Lower priority
        'Tourism crowd level': 20        # Lowest priority
    }
    
    # No travel history
    user_ratings = None
    
    # Get recommendations
    recommendations, explanation_data = recommender.recommend_countries(
        importance_scores=importance_scores,
        user_ratings=user_ratings,
        num_recommendations=5
    )
    
    # Display results
    print(f"User preferences (0-100 scale): {importance_scores}")
    print(f"Travel history: None")
    print(f"\nRecommendations:")
    
    for i, (country, score) in enumerate(recommendations, 1):
        print(f"{i}. {country}: {score:.3f}")
    
    print(f"\nAlgorithm: {explanation_data['algorithm_version']}")
    print(f"Countries scored: {explanation_data['num_countries_scored']}")
    
    return recommendations


def api_example_2():
    """
    Example 2: Experienced traveler with rating history
    """
    print("\n🌟 API Example 2: Experienced Traveler (Budget-focused)")
    print("=" * 55)
    
    # Initialize recommender
    recommender = SmartCountryRecommender()
    
    # API call parameters
    importance_scores = {
        'Budget friendliness': 90,       # Very high priority
        'Safety level': 75,              # High priority
        'English speaking level': 65,    # Medium-high priority
        'Public transport access': 70,   # Medium-high priority
        'Health care quality': 50,       # Medium priority
        'Culture accessibility rate': 60, # Medium priority
        'Nature and scenery': 80,        # High priority
        'Tourism crowd level': 30        # Lower priority
    }
    
    # Travel history with 1-5 star ratings
    user_ratings = {
        'Thailand': 5,        # Loved it
        'Vietnam': 5,         # Loved it
        'Cambodia': 4,        # Liked it
        'Malaysia': 4,        # Liked it
        'Singapore': 3,       # Neutral (too expensive)
        'Switzerland': 2,     # Didn't like (very expensive)
        'Norway': 2           # Didn't like (very expensive)
    }
    
    # Get recommendations
    recommendations, explanation_data = recommender.recommend_countries(
        importance_scores=importance_scores,
        user_ratings=user_ratings,
        num_recommendations=5
    )
    
    # Display results
    print(f"User preferences (0-100 scale): {importance_scores}")
    print(f"Travel history: {len(user_ratings)} countries rated")
    print(f"High-rated countries: {[country for country, rating in user_ratings.items() if rating >= 4]}")
    print(f"\nRecommendations:")
    
    for i, (country, score) in enumerate(recommendations, 1):
        print(f"{i}. {country}: {score:.3f}")
    
    print(f"\nAlgorithm: {explanation_data['algorithm_version']}")
    print(f"Countries scored: {explanation_data['num_countries_scored']}")
    
    return recommendations


def api_example_3():
    """
    Example 3: Culture and nature focused traveler
    """
    print("\n🎨 API Example 3: Culture & Nature Lover")
    print("=" * 45)
    
    # Initialize recommender
    recommender = SmartCountryRecommender()
    
    # API call parameters
    importance_scores = {
        'Culture accessibility rate': 95, # Very high priority
        'Nature and scenery': 90,        # Very high priority
        'Safety level': 80,              # High priority
        'English speaking level': 70,    # Medium-high priority
        'Health care quality': 60,       # Medium priority
        'Budget friendliness': 70,       # Medium-high priority
        'Public transport access': 65,   # Medium priority
        'Tourism crowd level': 15        # Very low priority (prefer less crowded)
    }
    
    # Travel history
    user_ratings = {
        'Japan': 5,           # Amazing culture and nature
        'New Zealand': 5,     # Incredible nature
        'Iceland': 4,         # Great nature, some culture
        'Italy': 4,           # Great culture, some nature
        'Greece': 4,          # Good culture and nature
        'Egypt': 3            # Culture but crowded/chaotic
    }
    
    # Get recommendations
    recommendations, explanation_data = recommender.recommend_countries(
        importance_scores=importance_scores,
        user_ratings=user_ratings,
        num_recommendations=5
    )
    
    # Display results
    print(f"User preferences (0-100 scale): {importance_scores}")
    print(f"Travel history: {len(user_ratings)} countries rated")
    print(f"High-rated countries: {[country for country, rating in user_ratings.items() if rating >= 4]}")
    print(f"\nRecommendations:")
    
    for i, (country, score) in enumerate(recommendations, 1):
        print(f"{i}. {country}: {score:.3f}")
    
    print(f"\nAlgorithm: {explanation_data['algorithm_version']}")
    print(f"Countries scored: {explanation_data['num_countries_scored']}")
    
    return recommendations


def main():
    """
    Run all API examples
    """
    print("🚀 Smart Country Recommender API Examples")
    print("=" * 60)
    print("Demonstrating corrected API format:")
    print("✅ Importance scores: 0-100 scale")
    print("✅ Country ratings: 1-5 stars")
    print("✅ Anonymous recommendations (no user ID)")
    print("✅ Only user knowledge: preferences + travel ratings")
    print()
    
    try:
        # Run examples
        rec1 = api_example_1()
        rec2 = api_example_2()
        rec3 = api_example_3()
        
        print("\n🎉 ALL API EXAMPLES COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ API accepts 0-100 importance scores")
        print("✅ API processes 1-5 star travel ratings")
        print("✅ Anonymous recommendations working")
        print("✅ Different user preference profiles tested")
        print("✅ Algorithm returns valid country recommendations")
        
        return True
        
    except Exception as e:
        print(f"\n❌ API Example Failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)