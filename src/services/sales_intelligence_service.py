"""
Sales Intelligence Service - Consolidated sales-focused functionality.

This service consolidates functionality from:
- ngx_roi_calculator.py
- real_time_roi_calculator.py
- tier_detection_service.py
- qualification_service.py
- early_adopter_service.py

Provides:
- ROI calculation and analysis
- Tier recommendation and detection
- Lead qualification and scoring
- Sales opportunity assessment
- Customer value prediction
- Business intelligence insights
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import math

from src.models.conversation import ConversationState, CustomerData
from src.utils.structured_logging import StructuredLogger

logger = StructuredLogger.get_logger(__name__)


class NGXTier(str, Enum):
    """NGX service tiers."""
    BASIC = "BASIC"
    PROFESSIONAL = "PROFESSIONAL"
    ENTERPRISE = "ENTERPRISE"
    CUSTOM = "CUSTOM"


class LeadQuality(str, Enum):
    """Lead quality classifications."""
    HOT = "hot"           # High probability, ready to buy
    WARM = "warm"         # Good potential, needs nurturing
    COLD = "cold"         # Low probability, long-term nurture
    UNQUALIFIED = "unqualified"  # Does not meet criteria


class BusinessSize(str, Enum):
    """Business size categories."""
    MICRO = "micro"       # 1-5 employees
    SMALL = "small"       # 6-50 employees
    MEDIUM = "medium"     # 51-200 employees
    LARGE = "large"       # 201+ employees


@dataclass
class ROIAnalysis:
    """ROI calculation result."""
    monthly_roi: float
    annual_roi: float
    breakeven_months: float
    total_savings: float
    revenue_increase: float
    cost_reduction: float
    payback_period_days: int
    confidence_score: float
    assumptions: List[str] = field(default_factory=list)
    breakdown: Dict[str, float] = field(default_factory=dict)


@dataclass
class TierRecommendation:
    """Tier recommendation result."""
    recommended_tier: NGXTier
    confidence: float
    tier_scores: Dict[NGXTier, float]
    reasoning: List[str]
    alternative_tiers: List[NGXTier] = field(default_factory=list)
    upgrade_potential: float = 0.0
    custom_requirements: List[str] = field(default_factory=list)


@dataclass
class LeadScore:
    """Lead qualification score."""
    overall_score: int  # 0-100
    quality: LeadQuality
    qualification_factors: Dict[str, float]
    disqualification_risks: List[str]
    action_recommendations: List[str]
    priority_level: int  # 1-5, 5 being highest priority
    estimated_close_probability: float
    estimated_deal_size: float


@dataclass
class BusinessProfile:
    """Comprehensive business profile."""
    business_size: BusinessSize
    industry: str
    monthly_revenue: float
    monthly_members: int
    staff_count: int
    tech_adoption_level: str  # low, medium, high
    growth_stage: str  # startup, growth, mature, enterprise
    pain_points: List[str]
    current_tools: List[str] = field(default_factory=list)
    budget_range: Optional[Tuple[float, float]] = None


class SalesIntelligenceService:
    """
    Unified sales intelligence service for revenue optimization.
    
    Features:
    - Advanced ROI calculation with multiple scenarios
    - Intelligent tier detection and recommendation
    - Comprehensive lead qualification
    - Business profiling and analysis
    - Sales opportunity assessment
    - Revenue forecasting and planning
    """
    
    def __init__(self):
        """Initialize sales intelligence service."""
        self.tier_configurations = self._initialize_tier_configurations()
        self.industry_multipliers = self._initialize_industry_multipliers()
        self.qualification_criteria = self._initialize_qualification_criteria()
        self.roi_assumptions = self._initialize_roi_assumptions()
        
        # Cached business profiles for faster analysis
        self.business_profiles_cache: Dict[str, BusinessProfile] = {}
        
        logger.info("SalesIntelligenceService initialized")
    
    def _initialize_tier_configurations(self) -> Dict[NGXTier, Dict[str, Any]]:
        """Initialize tier-specific configurations."""
        return {
            NGXTier.BASIC: {
                "price_monthly": 497,
                "max_members": 500,
                "staff_limit": 3,
                "features": ["basic_automation", "standard_reports", "email_support"],
                "roi_multiplier": 2.5,
                "setup_complexity": "low",
                "ideal_revenue_range": (5000, 15000),
                "target_business_size": [BusinessSize.MICRO, BusinessSize.SMALL]
            },
            NGXTier.PROFESSIONAL: {
                "price_monthly": 997,
                "max_members": 2000,
                "staff_limit": 10,
                "features": ["advanced_automation", "custom_reports", "phone_support", "integrations"],
                "roi_multiplier": 4.0,
                "setup_complexity": "medium",
                "ideal_revenue_range": (10000, 50000),
                "target_business_size": [BusinessSize.SMALL, BusinessSize.MEDIUM]
            },
            NGXTier.ENTERPRISE: {
                "price_monthly": 1997,
                "max_members": 10000,
                "staff_limit": 50,
                "features": ["enterprise_automation", "advanced_analytics", "dedicated_support", "custom_integrations"],
                "roi_multiplier": 6.0,
                "setup_complexity": "high",
                "ideal_revenue_range": (25000, 200000),
                "target_business_size": [BusinessSize.MEDIUM, BusinessSize.LARGE]
            },
            NGXTier.CUSTOM: {
                "price_monthly": 3000,  # Starting price
                "max_members": float('inf'),
                "staff_limit": float('inf'),
                "features": ["custom_development", "enterprise_plus", "white_label", "api_access"],
                "roi_multiplier": 8.0,
                "setup_complexity": "very_high",
                "ideal_revenue_range": (50000, float('inf')),
                "target_business_size": [BusinessSize.LARGE]
            }
        }
    
    def _initialize_industry_multipliers(self) -> Dict[str, float]:
        """Initialize industry-specific ROI multipliers."""
        return {
            "fitness": 1.0,           # Base multiplier
            "healthcare": 1.2,        # Higher compliance needs
            "wellness": 1.1,
            "physical_therapy": 1.3,
            "martial_arts": 0.9,
            "yoga_studio": 0.8,
            "crossfit": 1.1,
            "personal_training": 1.4,
            "spa": 1.2,
            "rehabilitation": 1.3,
            "sports_medicine": 1.4
        }
    
    def _initialize_qualification_criteria(self) -> Dict[str, Dict[str, Any]]:
        """Initialize lead qualification criteria."""
        return {
            "business_size": {
                "weight": 0.2,
                "scoring": {
                    BusinessSize.MICRO: 60,
                    BusinessSize.SMALL: 85,
                    BusinessSize.MEDIUM: 95,
                    BusinessSize.LARGE: 100
                }
            },
            "revenue": {
                "weight": 0.25,
                "thresholds": [
                    (5000, 50),    # Below $5k/month
                    (15000, 70),   # $5k-$15k/month
                    (50000, 90),   # $15k-$50k/month
                    (float('inf'), 100)  # Above $50k/month
                ]
            },
            "growth_stage": {
                "weight": 0.15,
                "scoring": {
                    "startup": 70,
                    "growth": 100,
                    "mature": 85,
                    "enterprise": 90
                }
            },
            "tech_adoption": {
                "weight": 0.15,
                "scoring": {
                    "low": 40,
                    "medium": 75,
                    "high": 95
                }
            },
            "budget_fit": {
                "weight": 0.15,
                "requires_calculation": True
            },
            "pain_points": {
                "weight": 0.1,
                "high_value_pains": [
                    "manual_processes",
                    "member_retention",
                    "lead_conversion",
                    "staff_efficiency",
                    "revenue_growth"
                ]
            }
        }
    
    def _initialize_roi_assumptions(self) -> Dict[str, Any]:
        """Initialize ROI calculation assumptions."""
        return {
            "time_savings_hours_per_month": 40,  # Hours saved by automation
            "average_hourly_cost": 25,            # Cost per hour of manual work
            "member_retention_improvement": 0.15,  # 15% improvement
            "new_member_acquisition_improvement": 0.25,  # 25% improvement
            "average_member_lifetime_value": 800,  # Average LTV per member
            "staff_efficiency_improvement": 0.30,  # 30% efficiency gain
            "revenue_per_member_monthly": 80,      # Average monthly revenue per member
            "implementation_time_weeks": 4,        # Time to full implementation
            "learning_curve_weeks": 2              # Time for staff to adapt
        }
    
    async def calculate_roi(
        self,
        business_profile: BusinessProfile,
        tier: NGXTier,
        custom_assumptions: Optional[Dict[str, Any]] = None
    ) -> ROIAnalysis:
        """
        Calculate comprehensive ROI analysis.
        
        Args:
            business_profile: Customer's business profile
            tier: NGX tier to calculate ROI for
            custom_assumptions: Custom assumptions to override defaults
            
        Returns:
            Detailed ROI analysis
        """
        tier_config = self.tier_configurations[tier]
        assumptions = {**self.roi_assumptions, **(custom_assumptions or {})}
        
        # Get industry multiplier
        industry_multiplier = self.industry_multipliers.get(business_profile.industry, 1.0)
        
        # Base monthly cost
        monthly_cost = tier_config["price_monthly"]
        
        # Calculate savings components
        time_savings = await self._calculate_time_savings(business_profile, assumptions)
        retention_savings = await self._calculate_retention_improvements(business_profile, assumptions)
        efficiency_gains = await self._calculate_efficiency_gains(business_profile, assumptions)
        acquisition_improvements = await self._calculate_acquisition_improvements(business_profile, assumptions)
        
        # Total monthly benefits
        total_monthly_benefits = (
            time_savings +
            retention_savings +
            efficiency_gains +
            acquisition_improvements
        ) * industry_multiplier
        
        # Calculate ROI metrics
        monthly_net_benefit = total_monthly_benefits - monthly_cost
        monthly_roi = (monthly_net_benefit / monthly_cost) * 100 if monthly_cost > 0 else 0
        annual_roi = monthly_roi  # Monthly ROI maintained annually
        
        # Breakeven calculation
        breakeven_months = monthly_cost / total_monthly_benefits if total_monthly_benefits > 0 else float('inf')
        payback_period_days = int(breakeven_months * 30)
        
        # Annual projections
        annual_savings = total_monthly_benefits * 12
        annual_cost = monthly_cost * 12
        annual_net_benefit = annual_savings - annual_cost
        
        # Confidence score based on data quality
        confidence_score = await self._calculate_confidence_score(business_profile, tier)
        
        # Breakdown of benefits
        breakdown = {
            "time_savings_monthly": time_savings,
            "retention_improvements_monthly": retention_savings,
            "efficiency_gains_monthly": efficiency_gains,
            "acquisition_improvements_monthly": acquisition_improvements,
            "total_monthly_benefits": total_monthly_benefits,
            "monthly_cost": monthly_cost,
            "monthly_net_benefit": monthly_net_benefit
        }
        
        # Assumptions used
        assumptions_list = [
            f"Time savings: {assumptions['time_savings_hours_per_month']} hours/month",
            f"Hourly cost: ${assumptions['average_hourly_cost']}/hour",
            f"Retention improvement: {assumptions['member_retention_improvement']*100}%",
            f"Acquisition improvement: {assumptions['new_member_acquisition_improvement']*100}%",
            f"Industry multiplier: {industry_multiplier}x"
        ]
        
        return ROIAnalysis(
            monthly_roi=monthly_roi,
            annual_roi=annual_roi,
            breakeven_months=breakeven_months,
            total_savings=annual_net_benefit,
            revenue_increase=retention_savings + acquisition_improvements,
            cost_reduction=time_savings + efficiency_gains,
            payback_period_days=payback_period_days,
            confidence_score=confidence_score,
            assumptions=assumptions_list,
            breakdown=breakdown
        )
    
    async def _calculate_time_savings(
        self,
        profile: BusinessProfile,
        assumptions: Dict[str, Any]
    ) -> float:
        """Calculate monthly time savings value."""
        hours_saved = assumptions["time_savings_hours_per_month"]
        hourly_cost = assumptions["average_hourly_cost"]
        
        # Scale by business size
        size_multiplier = {
            BusinessSize.MICRO: 0.5,
            BusinessSize.SMALL: 1.0,
            BusinessSize.MEDIUM: 2.0,
            BusinessSize.LARGE: 3.0
        }.get(profile.business_size, 1.0)
        
        return hours_saved * hourly_cost * size_multiplier
    
    async def _calculate_retention_improvements(
        self,
        profile: BusinessProfile,
        assumptions: Dict[str, Any]
    ) -> float:
        """Calculate monthly value from retention improvements."""
        improvement_rate = assumptions["member_retention_improvement"]
        current_members = profile.monthly_members
        monthly_revenue_per_member = assumptions["revenue_per_member_monthly"]
        
        # Calculate additional retained members per month
        additional_retained = current_members * improvement_rate * 0.1  # Conservative monthly estimate
        
        return additional_retained * monthly_revenue_per_member
    
    async def _calculate_efficiency_gains(
        self,
        profile: BusinessProfile,
        assumptions: Dict[str, Any]
    ) -> float:
        """Calculate monthly value from staff efficiency improvements."""
        efficiency_improvement = assumptions["staff_efficiency_improvement"]
        staff_count = profile.staff_count
        hourly_cost = assumptions["average_hourly_cost"]
        
        # Assume 20 hours per month per staff member can be optimized
        optimizable_hours = staff_count * 20
        efficiency_value = optimizable_hours * hourly_cost * efficiency_improvement
        
        return efficiency_value
    
    async def _calculate_acquisition_improvements(
        self,
        profile: BusinessProfile,
        assumptions: Dict[str, Any]
    ) -> float:
        """Calculate monthly value from improved member acquisition."""
        acquisition_improvement = assumptions["new_member_acquisition_improvement"]
        current_members = profile.monthly_members
        monthly_revenue_per_member = assumptions["revenue_per_member_monthly"]
        
        # Estimate current acquisition rate (5% of current base monthly)
        current_acquisition_rate = current_members * 0.05
        additional_acquisitions = current_acquisition_rate * acquisition_improvement
        
        return additional_acquisitions * monthly_revenue_per_member
    
    async def _calculate_confidence_score(
        self,
        profile: BusinessProfile,
        tier: NGXTier
    ) -> float:
        """Calculate confidence score for ROI analysis."""
        score = 0.5  # Base confidence
        
        # Business size confidence
        if profile.business_size in [BusinessSize.SMALL, BusinessSize.MEDIUM]:
            score += 0.2
        
        # Revenue data quality
        if profile.monthly_revenue > 0:
            score += 0.15
        
        # Member count data
        if profile.monthly_members > 0:
            score += 0.1
        
        # Industry match
        if profile.industry in self.industry_multipliers:
            score += 0.05
        
        return min(1.0, score)
    
    async def detect_optimal_tier(
        self,
        business_profile: BusinessProfile,
        budget_constraints: Optional[Dict[str, Any]] = None
    ) -> TierRecommendation:
        """
        Detect optimal NGX tier for a business.
        
        Args:
            business_profile: Customer's business profile
            budget_constraints: Budget limitations if any
            
        Returns:
            Tier recommendation with reasoning
        """
        tier_scores: Dict[NGXTier, float] = {}
        
        # Score each tier
        for tier in NGXTier:
            score = await self._score_tier_fit(business_profile, tier, budget_constraints)
            tier_scores[tier] = score
        
        # Find best fit
        recommended_tier = max(tier_scores.items(), key=lambda x: x[1])[0]
        confidence = tier_scores[recommended_tier]
        
        # Generate reasoning
        reasoning = await self._generate_tier_reasoning(
            business_profile, recommended_tier, tier_scores
        )
        
        # Find alternatives (tiers with scores > 0.6)
        alternatives = [
            tier for tier, score in tier_scores.items()
            if tier != recommended_tier and score > 0.6
        ]
        
        # Calculate upgrade potential
        upgrade_potential = await self._calculate_upgrade_potential(
            business_profile, recommended_tier
        )
        
        return TierRecommendation(
            recommended_tier=recommended_tier,
            confidence=confidence,
            tier_scores=tier_scores,
            reasoning=reasoning,
            alternative_tiers=alternatives,
            upgrade_potential=upgrade_potential
        )
    
    async def _score_tier_fit(
        self,
        profile: BusinessProfile,
        tier: NGXTier,
        budget_constraints: Optional[Dict[str, Any]]
    ) -> float:
        """Score how well a tier fits a business profile."""
        tier_config = self.tier_configurations[tier]
        score = 0.0
        
        # Revenue fit (30% weight)
        revenue_fit = await self._score_revenue_fit(profile.monthly_revenue, tier_config["ideal_revenue_range"])
        score += revenue_fit * 0.3
        
        # Business size fit (25% weight)
        if profile.business_size in tier_config["target_business_size"]:
            score += 0.25
        
        # Member capacity fit (20% weight)
        if profile.monthly_members <= tier_config["max_members"]:
            utilization = profile.monthly_members / tier_config["max_members"]
            # Optimal utilization is 50-80%
            if 0.5 <= utilization <= 0.8:
                score += 0.2
            elif utilization < 0.5:
                score += 0.15  # Underutilized but not penalized heavily
            else:
                score += 0.1   # Overutilized
        
        # Staff fit (15% weight)
        if profile.staff_count <= tier_config["staff_limit"]:
            score += 0.15
        
        # Budget fit (10% weight)
        if budget_constraints:
            budget_fit = await self._score_budget_fit(tier_config["price_monthly"], budget_constraints)
            score += budget_fit * 0.1
        else:
            score += 0.1  # No constraints = perfect fit
        
        return min(1.0, score)
    
    async def _score_revenue_fit(self, monthly_revenue: float, ideal_range: Tuple[float, float]) -> float:
        """Score how well revenue fits the tier's ideal range."""
        min_revenue, max_revenue = ideal_range
        
        if min_revenue <= monthly_revenue <= max_revenue:
            return 1.0
        elif monthly_revenue < min_revenue:
            # Below range - score based on how close
            ratio = monthly_revenue / min_revenue
            return max(0.0, ratio)
        else:
            # Above range - still good but not optimal
            if monthly_revenue <= max_revenue * 1.5:
                return 0.8
            else:
                return 0.5
    
    async def _score_budget_fit(
        self,
        tier_price: float,
        budget_constraints: Dict[str, Any]
    ) -> float:
        """Score budget fit for a tier."""
        max_budget = budget_constraints.get("max_monthly", float('inf'))
        preferred_budget = budget_constraints.get("preferred_monthly", max_budget * 0.8)
        
        if tier_price <= preferred_budget:
            return 1.0
        elif tier_price <= max_budget:
            return 0.7
        else:
            return 0.0
    
    async def _generate_tier_reasoning(
        self,
        profile: BusinessProfile,
        recommended_tier: NGXTier,
        tier_scores: Dict[NGXTier, float]
    ) -> List[str]:
        """Generate reasoning for tier recommendation."""
        reasoning = []
        tier_config = self.tier_configurations[recommended_tier]
        
        # Revenue-based reasoning
        if profile.monthly_revenue >= tier_config["ideal_revenue_range"][0]:
            reasoning.append(f"Revenue of ${profile.monthly_revenue:,.0f}/month fits well with {recommended_tier.value}")
        
        # Business size reasoning
        if profile.business_size in tier_config["target_business_size"]:
            reasoning.append(f"{profile.business_size.value.title()} business size is ideal for {recommended_tier.value}")
        
        # Capacity reasoning
        utilization = profile.monthly_members / tier_config["max_members"]
        if utilization <= 0.8:
            reasoning.append(f"Current {profile.monthly_members} members fits comfortably within {recommended_tier.value} capacity")
        
        # Growth reasoning
        if profile.growth_stage == "growth":
            reasoning.append(f"{recommended_tier.value} provides room for business growth")
        
        # Feature fit
        if profile.tech_adoption_level == "high" and recommended_tier in [NGXTier.PROFESSIONAL, NGXTier.ENTERPRISE]:
            reasoning.append(f"High tech adoption level matches {recommended_tier.value} advanced features")
        
        return reasoning
    
    async def _calculate_upgrade_potential(
        self,
        profile: BusinessProfile,
        current_tier: NGXTier
    ) -> float:
        """Calculate potential for tier upgrades."""
        if current_tier == NGXTier.CUSTOM:
            return 0.0
        
        upgrade_indicators = 0.0
        
        # Growth stage
        if profile.growth_stage == "growth":
            upgrade_indicators += 0.3
        
        # High tech adoption
        if profile.tech_adoption_level == "high":
            upgrade_indicators += 0.2
        
        # Revenue growth potential
        tier_config = self.tier_configurations[current_tier]
        if profile.monthly_revenue > tier_config["ideal_revenue_range"][1] * 0.8:
            upgrade_indicators += 0.3
        
        # Member growth potential
        utilization = profile.monthly_members / tier_config["max_members"]
        if utilization > 0.7:
            upgrade_indicators += 0.2
        
        return min(1.0, upgrade_indicators)
    
    async def qualify_lead(
        self,
        business_profile: BusinessProfile,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> LeadScore:
        """
        Perform comprehensive lead qualification.
        
        Args:
            business_profile: Customer's business profile
            conversation_context: Current conversation context
            
        Returns:
            Complete lead qualification score
        """
        qualification_factors = {}
        total_score = 0.0
        
        # Score each qualification criterion
        for criterion, config in self.qualification_criteria.items():
            factor_score = await self._score_qualification_factor(
                criterion, business_profile, config, conversation_context
            )
            qualification_factors[criterion] = factor_score
            total_score += factor_score * config["weight"]
        
        # Convert to 0-100 scale
        overall_score = int(total_score * 100)
        
        # Determine quality classification
        quality = self._classify_lead_quality(overall_score)
        
        # Identify disqualification risks
        disqualification_risks = await self._identify_disqualification_risks(
            business_profile, qualification_factors
        )
        
        # Generate action recommendations
        action_recommendations = await self._generate_action_recommendations(
            quality, qualification_factors, disqualification_risks
        )
        
        # Calculate priority level
        priority_level = self._calculate_priority_level(overall_score, quality)
        
        # Estimate close probability and deal size
        close_probability = await self._estimate_close_probability(
            overall_score, qualification_factors
        )
        
        estimated_deal_size = await self._estimate_deal_size(
            business_profile, qualification_factors
        )
        
        return LeadScore(
            overall_score=overall_score,
            quality=quality,
            qualification_factors=qualification_factors,
            disqualification_risks=disqualification_risks,
            action_recommendations=action_recommendations,
            priority_level=priority_level,
            estimated_close_probability=close_probability,
            estimated_deal_size=estimated_deal_size
        )
    
    async def _score_qualification_factor(
        self,
        criterion: str,
        profile: BusinessProfile,
        config: Dict[str, Any],
        conversation_context: Optional[Dict[str, Any]]
    ) -> float:
        """Score a specific qualification factor."""
        
        if criterion == "business_size":
            return config["scoring"].get(profile.business_size, 0) / 100.0
        
        elif criterion == "revenue":
            for threshold, score in config["thresholds"]:
                if profile.monthly_revenue <= threshold:
                    return score / 100.0
            return 0.5
        
        elif criterion == "growth_stage":
            return config["scoring"].get(profile.growth_stage, 0) / 100.0
        
        elif criterion == "tech_adoption":
            return config["scoring"].get(profile.tech_adoption_level, 0) / 100.0
        
        elif criterion == "budget_fit":
            # Calculate if they can afford any tier
            min_tier_price = min(
                tier_config["price_monthly"]
                for tier_config in self.tier_configurations.values()
            )
            
            if profile.monthly_revenue >= min_tier_price * 10:  # 10x revenue to price ratio
                return 1.0
            elif profile.monthly_revenue >= min_tier_price * 5:
                return 0.7
            elif profile.monthly_revenue >= min_tier_price * 2:
                return 0.4
            else:
                return 0.1
        
        elif criterion == "pain_points":
            high_value_pains = config["high_value_pains"]
            matching_pains = sum(1 for pain in profile.pain_points if pain in high_value_pains)
            return min(1.0, matching_pains / len(high_value_pains))
        
        return 0.5
    
    def _classify_lead_quality(self, overall_score: int) -> LeadQuality:
        """Classify lead quality based on overall score."""
        if overall_score >= 80:
            return LeadQuality.HOT
        elif overall_score >= 60:
            return LeadQuality.WARM
        elif overall_score >= 40:
            return LeadQuality.COLD
        else:
            return LeadQuality.UNQUALIFIED
    
    async def _identify_disqualification_risks(
        self,
        profile: BusinessProfile,
        qualification_factors: Dict[str, float]
    ) -> List[str]:
        """Identify potential disqualification risks."""
        risks = []
        
        if qualification_factors.get("budget_fit", 0) < 0.3:
            risks.append("Budget constraints may prevent purchase")
        
        if qualification_factors.get("tech_adoption", 0) < 0.4:
            risks.append("Low tech adoption may create implementation resistance")
        
        if qualification_factors.get("business_size", 0) < 0.5:
            risks.append("Business may be too small for significant ROI")
        
        if profile.monthly_revenue < 2000:
            risks.append("Very low revenue may indicate financial instability")
        
        return risks
    
    async def _generate_action_recommendations(
        self,
        quality: LeadQuality,
        qualification_factors: Dict[str, float],
        risks: List[str]
    ) -> List[str]:
        """Generate action recommendations based on lead profile."""
        recommendations = []
        
        if quality == LeadQuality.HOT:
            recommendations.append("Schedule demo immediately")
            recommendations.append("Prepare pricing proposal")
            recommendations.append("Focus on closing within 1-2 calls")
        
        elif quality == LeadQuality.WARM:
            recommendations.append("Build value through ROI demonstration")
            recommendations.append("Address specific pain points")
            recommendations.append("Provide social proof and case studies")
        
        elif quality == LeadQuality.COLD:
            recommendations.append("Focus on education and nurturing")
            recommendations.append("Provide valuable content")
            recommendations.append("Schedule follow-up in 30-60 days")
        
        else:  # UNQUALIFIED
            recommendations.append("Politely disqualify but maintain relationship")
            recommendations.append("Refer to appropriate solutions if possible")
        
        # Add risk-specific recommendations
        if "Budget constraints" in str(risks):
            recommendations.append("Explore financing options or entry-level tier")
        
        if "tech adoption" in str(risks):
            recommendations.append("Emphasize ease of use and training support")
        
        return recommendations
    
    def _calculate_priority_level(self, overall_score: int, quality: LeadQuality) -> int:
        """Calculate priority level (1-5, 5 being highest)."""
        if quality == LeadQuality.HOT and overall_score >= 90:
            return 5
        elif quality == LeadQuality.HOT:
            return 4
        elif quality == LeadQuality.WARM and overall_score >= 70:
            return 3
        elif quality == LeadQuality.WARM:
            return 2
        else:
            return 1
    
    async def _estimate_close_probability(
        self,
        overall_score: int,
        qualification_factors: Dict[str, float]
    ) -> float:
        """Estimate probability of closing the deal."""
        base_probability = overall_score / 100.0
        
        # Adjust based on specific factors
        if qualification_factors.get("budget_fit", 0) > 0.8:
            base_probability *= 1.2
        
        if qualification_factors.get("pain_points", 0) > 0.7:
            base_probability *= 1.15
        
        return min(1.0, base_probability)
    
    async def _estimate_deal_size(
        self,
        profile: BusinessProfile,
        qualification_factors: Dict[str, float]
    ) -> float:
        """Estimate potential deal size."""
        # Get tier recommendation
        tier_rec = await self.detect_optimal_tier(profile)
        tier_config = self.tier_configurations[tier_rec.recommended_tier]
        
        # Base annual contract value
        base_deal_size = tier_config["price_monthly"] * 12
        
        # Adjust for business size
        size_multiplier = {
            BusinessSize.MICRO: 1.0,
            BusinessSize.SMALL: 1.2,
            BusinessSize.MEDIUM: 1.5,
            BusinessSize.LARGE: 2.0
        }.get(profile.business_size, 1.0)
        
        return base_deal_size * size_multiplier
    
    async def create_business_profile(
        self,
        customer_data: CustomerData,
        conversation_context: Optional[Dict[str, Any]] = None
    ) -> BusinessProfile:
        """
        Create business profile from customer data and conversation context.
        
        Args:
            customer_data: Basic customer information
            conversation_context: Additional context from conversation
            
        Returns:
            Complete business profile
        """
        # Extract basic information
        business_size = self._determine_business_size(customer_data, conversation_context)
        industry = customer_data.industry or "fitness"
        
        # Extract financial information
        monthly_revenue = self._extract_revenue_info(conversation_context)
        monthly_members = self._extract_member_count(conversation_context)
        staff_count = self._extract_staff_count(conversation_context)
        
        # Extract technology and growth information
        tech_adoption_level = self._assess_tech_adoption(conversation_context)
        growth_stage = self._assess_growth_stage(conversation_context, monthly_revenue)
        
        # Extract pain points from conversation
        pain_points = self._extract_pain_points(conversation_context)
        
        profile = BusinessProfile(
            business_size=business_size,
            industry=industry,
            monthly_revenue=monthly_revenue,
            monthly_members=monthly_members,
            staff_count=staff_count,
            tech_adoption_level=tech_adoption_level,
            growth_stage=growth_stage,
            pain_points=pain_points
        )
        
        # Cache the profile
        if customer_data.id:
            self.business_profiles_cache[customer_data.id] = profile
        
        return profile
    
    def _determine_business_size(
        self,
        customer_data: CustomerData,
        conversation_context: Optional[Dict[str, Any]]
    ) -> BusinessSize:
        """Determine business size from available data."""
        # Try to get from conversation context first
        if conversation_context:
            staff_mentioned = conversation_context.get("staff_count", 0)
            if staff_mentioned:
                if staff_mentioned <= 5:
                    return BusinessSize.MICRO
                elif staff_mentioned <= 50:
                    return BusinessSize.SMALL
                elif staff_mentioned <= 200:
                    return BusinessSize.MEDIUM
                else:
                    return BusinessSize.LARGE
        
        # Default based on customer data
        return BusinessSize.SMALL
    
    def _extract_revenue_info(self, conversation_context: Optional[Dict[str, Any]]) -> float:
        """Extract revenue information from conversation."""
        if not conversation_context:
            return 10000.0  # Default assumption
        
        # Look for revenue mentions in context
        revenue_indicators = conversation_context.get("revenue_indicators", {})
        
        if "monthly_revenue" in revenue_indicators:
            return float(revenue_indicators["monthly_revenue"])
        
        # Estimate from member count if available
        member_count = conversation_context.get("member_count", 0)
        if member_count:
            # Assume $80 average revenue per member per month
            return member_count * 80
        
        return 10000.0  # Default
    
    def _extract_member_count(self, conversation_context: Optional[Dict[str, Any]]) -> int:
        """Extract member count from conversation."""
        if not conversation_context:
            return 200  # Default assumption
        
        return conversation_context.get("member_count", 200)
    
    def _extract_staff_count(self, conversation_context: Optional[Dict[str, Any]]) -> int:
        """Extract staff count from conversation."""
        if not conversation_context:
            return 3  # Default assumption
        
        return conversation_context.get("staff_count", 3)
    
    def _assess_tech_adoption(self, conversation_context: Optional[Dict[str, Any]]) -> str:
        """Assess technology adoption level."""
        if not conversation_context:
            return "medium"
        
        tech_indicators = conversation_context.get("tech_indicators", [])
        
        if any(indicator in tech_indicators for indicator in ["advanced_systems", "api_integration", "custom_software"]):
            return "high"
        elif any(indicator in tech_indicators for indicator in ["basic_software", "social_media", "online_booking"]):
            return "medium"
        else:
            return "low"
    
    def _assess_growth_stage(self, conversation_context: Optional[Dict[str, Any]], revenue: float) -> str:
        """Assess business growth stage."""
        if not conversation_context:
            if revenue < 5000:
                return "startup"
            elif revenue < 25000:
                return "growth"
            else:
                return "mature"
        
        growth_indicators = conversation_context.get("growth_indicators", [])
        
        if "rapid_expansion" in growth_indicators:
            return "growth"
        elif "established_business" in growth_indicators:
            return "mature"
        elif "new_business" in growth_indicators:
            return "startup"
        else:
            return "growth"  # Default to growth stage
    
    def _extract_pain_points(self, conversation_context: Optional[Dict[str, Any]]) -> List[str]:
        """Extract pain points from conversation."""
        if not conversation_context:
            return ["manual_processes"]
        
        return conversation_context.get("pain_points", ["manual_processes"])
    
    async def get_service_stats(self) -> Dict[str, Any]:
        """Get comprehensive service statistics."""
        return {
            "supported_tiers": len(self.tier_configurations),
            "industry_multipliers": len(self.industry_multipliers),
            "qualification_criteria": len(self.qualification_criteria),
            "cached_business_profiles": len(self.business_profiles_cache),
            "tier_configurations": {
                tier.value: {
                    "monthly_price": config["price_monthly"],
                    "max_members": config["max_members"],
                    "roi_multiplier": config["roi_multiplier"]
                }
                for tier, config in self.tier_configurations.items()
            }
        }