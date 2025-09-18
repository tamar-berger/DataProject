"""
Constraint Filtering Module
Filters countries based on user's hard requirements with smart relaxation
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Set, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ConstraintFilter:
    """
    Applies user constraints to filter countries, with intelligent relaxation
    when constraints are too restrictive.
    
    Key innovation: Progressive constraint relaxation to ensure meaningful results
    while respecting user's most important requirements.
    """
    
    def __init__(self,
                 high_importance_threshold: int = 8,
                 min_results_threshold: int = 3,
                 relaxation_steps: int = 3):
        """
        Initialize constraint filter
        
        Args:
            high_importance_threshold: Importance score (8-10) that triggers constraints
            min_results_threshold: Minimum countries that should pass filtering
            relaxation_steps: Number of relaxation attempts if too few results
        """
        self.high_importance_threshold = high_importance_threshold
        self.min_results_threshold = min_results_threshold
        self.relaxation_steps = relaxation_steps
        
    def apply_constraints(self,
                         countries_df: pd.DataFrame,
                         importance_scores: Dict[str, int],
                         preference_mapping: Dict[str, List[str]],
                         scores: Optional[Dict[str, float]] = None) -> Tuple[pd.DataFrame, Dict[str, any]]:
        """
        Apply constraints to filter countries
        
        Args:
            countries_df: DataFrame with all countries and features
            importance_scores: User importance ratings (1-10)
            preference_mapping: Maps preference categories to database features
            scores: Optional scores to help with relaxation decisions
            
        Returns:
            Tuple of (filtered_dataframe, constraint_info)
        """
        constraint_info = {
            'applied_constraints': [],
            'relaxed_constraints': [],
            'num_results': 0,
            'relaxation_level': 0
        }
        
        # Identify hard constraints (high importance features)
        hard_constraints = self._identify_hard_constraints(importance_scores, preference_mapping)
        
        if not hard_constraints:
            logger.info("No hard constraints identified")
            constraint_info['num_results'] = len(countries_df)
            return countries_df, constraint_info
        
        # Apply constraints with progressive relaxation
        filtered_df, constraint_info = self._apply_with_relaxation(
            countries_df, hard_constraints, scores, constraint_info
        )
        
        logger.info(f"Constraint filtering: {len(countries_df)} → {len(filtered_df)} countries "
                   f"(relaxation level: {constraint_info['relaxation_level']})")
        
        return filtered_df, constraint_info
    
    def _identify_hard_constraints(self,
                                  importance_scores: Dict[str, int],
                                  preference_mapping: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """
        Identify features that should be treated as hard constraints
        
        Returns:
            Dictionary mapping constraint categories to feature lists
        """
        hard_constraints = {}
        
        for category, importance in importance_scores.items():
            if importance >= self.high_importance_threshold and category in preference_mapping:
                features = preference_mapping[category]
                hard_constraints[category] = features
                logger.info(f"Hard constraint: {category} (importance {importance}) → {features}")
        
        return hard_constraints
    
    def _apply_with_relaxation(self,
                              countries_df: pd.DataFrame,
                              hard_constraints: Dict[str, List[str]],
                              scores: Optional[Dict[str, float]],
                              constraint_info: Dict[str, any]) -> Tuple[pd.DataFrame, Dict[str, any]]:
        """
        Apply constraints with progressive relaxation if needed
        """
        current_df = countries_df.copy()
        relaxation_level = 0
        
        # Calculate initial constraint thresholds
        constraint_thresholds = self._calculate_constraint_thresholds(
            countries_df, hard_constraints, relaxation_level
        )
        
        for attempt in range(self.relaxation_steps + 1):
            # Apply current constraints
            filtered_df, applied_constraints = self._filter_by_thresholds(
                current_df, constraint_thresholds
            )
            
            # Check if we have enough results
            if len(filtered_df) >= self.min_results_threshold:
                constraint_info.update({
                    'applied_constraints': applied_constraints,
                    'num_results': len(filtered_df),
                    'relaxation_level': relaxation_level
                })
                return filtered_df, constraint_info
            
            # Too few results - try relaxation
            if attempt < self.relaxation_steps:
                relaxation_level += 1
                constraint_thresholds, relaxed_constraint = self._relax_constraints(
                    countries_df, hard_constraints, constraint_thresholds, 
                    scores, relaxation_level
                )
                
                if relaxed_constraint:
                    constraint_info['relaxed_constraints'].append(relaxed_constraint)
                    logger.info(f"Relaxed constraint: {relaxed_constraint} (level {relaxation_level})")
            else:
                # Last resort: return what we have
                break
        
        # Final result (even if below threshold)
        constraint_info.update({
            'applied_constraints': applied_constraints if 'applied_constraints' in locals() else [],
            'num_results': len(filtered_df) if 'filtered_df' in locals() else len(countries_df),
            'relaxation_level': relaxation_level
        })
        
        return filtered_df if 'filtered_df' in locals() else countries_df, constraint_info
    
    def _calculate_constraint_thresholds(self,
                                       countries_df: pd.DataFrame,
                                       hard_constraints: Dict[str, List[str]],
                                       relaxation_level: int) -> Dict[str, float]:
        """
        Calculate constraint thresholds based on data distribution and relaxation level
        """
        thresholds = {}
        
        for category, features in hard_constraints.items():
            feature_values = []
            
            # Collect all values for features in this constraint category
            for feature in features:
                if feature in countries_df.columns:
                    values = countries_df[feature].dropna()
                    feature_values.extend(values.tolist())
            
            if feature_values:
                # Calculate percentile threshold (higher = more restrictive)
                base_percentile = 75  # Start at 75th percentile
                relaxed_percentile = max(50, base_percentile - (relaxation_level * 10))
                threshold = np.percentile(feature_values, relaxed_percentile)
                
                # Store threshold for all features in this category
                for feature in features:
                    if feature in countries_df.columns:
                        thresholds[feature] = threshold
        
        return thresholds
    
    def _filter_by_thresholds(self,
                             countries_df: pd.DataFrame,
                             thresholds: Dict[str, float]) -> Tuple[pd.DataFrame, List[str]]:
        """
        Filter countries by constraint thresholds
        """
        filtered_df = countries_df.copy()
        applied_constraints = []
        
        for feature, threshold in thresholds.items():
            if feature in filtered_df.columns:
                # Handle different constraint types
                if 'cost' in feature.lower() or 'crime' in feature.lower():
                    # Lower is better for cost and crime
                    mask = filtered_df[feature] <= threshold
                else:
                    # Higher is better for most features
                    mask = filtered_df[feature] >= threshold
                
                # Apply filter
                initial_count = len(filtered_df)
                filtered_df = filtered_df[mask]
                final_count = len(filtered_df)
                
                if initial_count > final_count:
                    applied_constraints.append(f"{feature} threshold: {threshold:.2f}")
                    logger.debug(f"Constraint {feature} >= {threshold:.2f}: {initial_count} → {final_count}")
        
        return filtered_df, applied_constraints
    
    def _relax_constraints(self,
                          countries_df: pd.DataFrame,
                          hard_constraints: Dict[str, List[str]],
                          current_thresholds: Dict[str, float],
                          scores: Optional[Dict[str, float]],
                          relaxation_level: int) -> Tuple[Dict[str, float], Optional[str]]:
        """
        Intelligently relax the most restrictive constraint
        """
        if not current_thresholds:
            return current_thresholds, None
        
        # Strategy 1: Relax the constraint that eliminates the most high-scoring countries
        if scores:
            constraint_impact = self._analyze_constraint_impact(
                countries_df, current_thresholds, scores
            )
            
            # Relax the constraint with highest impact on good countries
            if constraint_impact:
                feature_to_relax = max(constraint_impact.items(), key=lambda x: x[1])[0]
                return self._relax_specific_constraint(
                    current_thresholds, feature_to_relax, relaxation_level
                ), feature_to_relax
        
        # Strategy 2: Relax the most restrictive constraint (highest threshold)
        feature_to_relax = max(current_thresholds.items(), key=lambda x: x[1])[0]
        return self._relax_specific_constraint(
            current_thresholds, feature_to_relax, relaxation_level
        ), feature_to_relax
    
    def _analyze_constraint_impact(self,
                                  countries_df: pd.DataFrame,
                                  thresholds: Dict[str, float],
                                  scores: Dict[str, float]) -> Dict[str, float]:
        """
        Analyze which constraints eliminate the most high-scoring countries
        """
        constraint_impact = {}
        
        # Get high-scoring countries (top 25%)
        score_threshold = np.percentile(list(scores.values()), 75)
        high_scoring_countries = {country for country, score in scores.items() 
                                if score >= score_threshold}
        
        for feature, threshold in thresholds.items():
            if feature not in countries_df.columns:
                continue
            
            # Count high-scoring countries eliminated by this constraint
            eliminated_count = 0
            
            for _, row in countries_df.iterrows():
                country_name = row.get('country_name', row.get('country', ''))
                if country_name in high_scoring_countries:
                    feature_value = row[feature]
                    
                    # Check if this constraint would eliminate this country
                    if pd.notna(feature_value):
                        if 'cost' in feature.lower() or 'crime' in feature.lower():
                            eliminates = feature_value > threshold
                        else:
                            eliminates = feature_value < threshold
                        
                        if eliminates:
                            eliminated_count += 1
            
            constraint_impact[feature] = eliminated_count
        
        return constraint_impact
    
    def _relax_specific_constraint(self,
                                  thresholds: Dict[str, float],
                                  feature_to_relax: str,
                                  relaxation_level: int) -> Dict[str, float]:
        """
        Relax a specific constraint by adjusting its threshold
        """
        new_thresholds = thresholds.copy()
        
        if feature_to_relax in new_thresholds:
            current_threshold = new_thresholds[feature_to_relax]
            
            # Relaxation factor increases with level
            relaxation_factor = 0.9 ** relaxation_level  # 0.9, 0.81, 0.729, ...
            
            if 'cost' in feature_to_relax.lower() or 'crime' in feature_to_relax.lower():
                # For "lower is better" features, increase threshold
                new_thresholds[feature_to_relax] = current_threshold / relaxation_factor
            else:
                # For "higher is better" features, decrease threshold
                new_thresholds[feature_to_relax] = current_threshold * relaxation_factor
        
        return new_thresholds
    
    def explain_constraints(self,
                           constraint_info: Dict[str, any],
                           importance_scores: Dict[str, int]) -> str:
        """
        Generate human-readable explanation of applied constraints
        """
        explanations = []
        
        # Show what triggered constraints
        high_importance = [category for category, importance in importance_scores.items() 
                          if importance >= self.high_importance_threshold]
        
        if high_importance:
            explanations.append(f"High importance preferences (≥{self.high_importance_threshold}): "
                              f"{', '.join(high_importance)}")
        
        # Show applied constraints
        if constraint_info['applied_constraints']:
            explanations.append("Applied constraints:")
            for constraint in constraint_info['applied_constraints']:
                explanations.append(f"  • {constraint}")
        
        # Show relaxations
        if constraint_info['relaxed_constraints']:
            explanations.append(f"Relaxed constraints (level {constraint_info['relaxation_level']}):")
            for relaxed in constraint_info['relaxed_constraints']:
                explanations.append(f"  • {relaxed}")
        
        explanations.append(f"Final results: {constraint_info['num_results']} countries")
        
        return "\n".join(explanations)


