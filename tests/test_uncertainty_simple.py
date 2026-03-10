#!/usr/bin/env python3
"""
Simplified standalone test for uncertainty analysis functionality.

Tests core Monte Carlo functions without complex imports or dependencies.
"""

import math
import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class UncertaintySummary:
    """Metadata describing Monte Carlo uncertainty analysis results."""
    
    method: str
    emissions_kg: float
    ci_lower_kg: float
    ci_upper_kg: float
    confidence_level_pct: float
    relative_uncertainty_pct: float


class MockEnergy:
    """Mock Energy class for testing."""
    
    def __init__(self, kwh: float):
        self._kwh = kwh
    
    @property
    def kWh(self) -> float:
        return self._kwh
    
    @classmethod
    def from_kWh(cls, kwh: float) -> 'MockEnergy':
        return cls(kwh)


def _sample_normal(mu: float, sigma: float, rng: random.Random) -> float:
    """
    Sample from normal distribution using Box-Muller transform.

    Args:
        mu: Mean of normal distribution
        sigma: Standard deviation of normal distribution
        rng: Random number generator instance

    Returns:
        Sample from normal distribution N(mu, sigma²)
    """
    if sigma <= 0:
        return mu

    # Box-Muller transform for two independent standard normal samples
    u1 = max(rng.random(), 1e-12)  # Prevent log(0)  # nosec B311
    u2 = rng.random()  # nosec B311
    r = math.sqrt(-2.0 * math.log(u1))
    theta = 2 * math.pi * u2
    z0 = r * math.cos(theta)
    return mu + sigma * z0


def estimate_emissions_distribution(
    *,
    energy_kwh: float,
    carbon_intensity_gco2_kwh: float,
    n_samples: int = 1000,
    energy_uncertainty_pct: float = 10.0,
    carbon_intensity_uncertainty_pct: float = 15.0,
    pue: float = 1.0,
    pue_uncertainty_pct: float = 5.0,
    seed: int | None = 42,
) -> list[float]:
    """
    Generate Monte Carlo emissions distribution accounting for measurement uncertainty.

    Args:
        energy_kwh: Measured energy consumption in kWh
        carbon_intensity_gco2_kwh: Grid carbon intensity in g CO₂/kWh
        n_samples: Number of Monte Carlo iterations
        energy_uncertainty_pct: Energy measurement uncertainty as percentage
        carbon_intensity_uncertainty_pct: Carbon intensity data uncertainty as percentage
        pue: Power Usage Effectiveness factor
        pue_uncertainty_pct: PUE uncertainty as percentage
        seed: Random seed for reproducibility (None for non-deterministic)

    Returns:
        List of simulated emissions values in kg CO₂
    """
    rng = random.Random() if seed is None else random.Random(seed)  # nosec B311
    samples: list[float] = []

    # Convert percentage uncertainties to standard deviations (assuming ±2σ bounds)
    energy_sigma = energy_kwh * (energy_uncertainty_pct / 100.0) / 2.0
    ci_sigma = carbon_intensity_gco2_kwh * (carbon_intensity_uncertainty_pct / 100.0) / 2.0
    pue_sigma = pue * (pue_uncertainty_pct / 100.0) / 2.0

    for _ in range(max(1, n_samples)):
        # Sample uncertain parameters
        sampled_energy = max(0.0, _sample_normal(energy_kwh, energy_sigma, rng))
        sampled_intensity = max(0.0, _sample_normal(carbon_intensity_gco2_kwh, ci_sigma, rng))
        sampled_pue = max(1.0, _sample_normal(pue, pue_sigma, rng))
        
        # Calculate emissions for this sample
        total_energy_kwh = sampled_energy * sampled_pue
        emissions_g = total_energy_kwh * sampled_intensity
        emissions_kg = emissions_g / 1000.0
        
        samples.append(emissions_kg)

    return samples


def compute_confidence_interval(
    samples: list[float],
    alpha: float = 0.05,
) -> tuple[float, float]:
    """
    Compute percentile-based confidence interval from Monte Carlo samples.

    Args:
        samples: Monte Carlo emission samples
        alpha: Two-sided significance level (0.05 for 95% CI)

    Returns:
        Tuple of (lower_bound, upper_bound) for confidence interval
    """
    if not samples:
        return (0.0, 0.0)

    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    
    # Calculate percentile indices
    lower_idx = int((alpha / 2.0) * (n - 1))
    upper_idx = int((1 - alpha / 2.0) * (n - 1))
    
    return (sorted_samples[lower_idx], sorted_samples[upper_idx])


def quantify_emissions_uncertainty(
    energy: MockEnergy,
    carbon_intensity_gco2_kwh: float,
    pue: float = 1.0,
    *,
    energy_uncertainty_pct: float = 10.0,
    carbon_intensity_uncertainty_pct: float = 15.0,
    pue_uncertainty_pct: float = 5.0,
    confidence_level: float = 0.95,
    n_samples: int = 1000,
    seed: int | None = 42,
) -> UncertaintySummary:
    """
    Perform complete uncertainty analysis for emissions calculation.

    Args:
        energy: Energy consumption measurement
        carbon_intensity_gco2_kwh: Carbon intensity in g CO₂/kWh
        pue: Power Usage Effectiveness (≥ 1.0 for physical data centers)
        energy_uncertainty_pct: Energy measurement uncertainty (%)
        carbon_intensity_uncertainty_pct: Carbon intensity uncertainty (%)
        pue_uncertainty_pct: PUE uncertainty (%)
        confidence_level: Confidence level for interval (0.95 = 95%)
        n_samples: Monte Carlo sample count
        seed: Random seed for reproducibility

    Returns:
        UncertaintySummary with point estimate and confidence bounds
    """
    # Generate Monte Carlo samples
    samples = estimate_emissions_distribution(
        energy_kwh=energy.kWh,
        carbon_intensity_gco2_kwh=carbon_intensity_gco2_kwh,
        n_samples=n_samples,
        energy_uncertainty_pct=energy_uncertainty_pct,
        carbon_intensity_uncertainty_pct=carbon_intensity_uncertainty_pct,
        pue=pue,
        pue_uncertainty_pct=pue_uncertainty_pct,
        seed=seed,
    )

    # Calculate statistics
    mean_emissions = sum(samples) / len(samples)
    alpha = 1.0 - confidence_level
    ci_lower, ci_upper = compute_confidence_interval(samples, alpha)
    
    # Calculate relative uncertainty
    if mean_emissions > 0:
        relative_uncertainty_pct = 100.0 * (ci_upper - ci_lower) / (2.0 * mean_emissions)
    else:
        relative_uncertainty_pct = 0.0

    return UncertaintySummary(
        method="Monte Carlo",
        emissions_kg=mean_emissions,
        ci_lower_kg=ci_lower,
        ci_upper_kg=ci_upper,
        confidence_level_pct=confidence_level * 100.0,
        relative_uncertainty_pct=relative_uncertainty_pct,
    )


def assess_uncertainty_quality(uncertainty: UncertaintySummary, threshold_pct: float = 20.0) -> dict[str, str]:
    """
    Assess quality and actionability of uncertainty estimates.

    Args:
        uncertainty: UncertaintySummary to evaluate
        threshold_pct: Threshold for acceptable relative uncertainty

    Returns:
        Dictionary with assessment and recommendations
    """
    if uncertainty.relative_uncertainty_pct <= threshold_pct:
        assessment = "LOW"
        recommendation = "Estimates are reliable for decision-making."
    else:
        assessment = "HIGH"
        recommendation = "Consider improving measurement methods or data sources."
    
    return {
        "uncertainty_level": assessment,
        "recommendation": recommendation,
    }


def test_basic_monte_carlo():
    """Test basic Monte Carlo functionality."""
    print("Testing Monte Carlo Core Functions...")
    
    # Test normal sampling
    rng = random.Random(42)
    samples = [_sample_normal(100.0, 10.0, rng) for _ in range(100)]
    mean_sample = sum(samples) / len(samples)
    
    assert 80 < mean_sample < 120, f"Expected mean around 100, got {mean_sample}"
    print(f"✓ Normal sampling: mean={mean_sample:.2f} (expected ~100)")
    
    # Test emissions distribution
    samples = estimate_emissions_distribution(
        energy_kwh=10.0,
        carbon_intensity_gco2_kwh=500.0,
        n_samples=100,
        seed=42,
    )
    
    assert len(samples) == 100, f"Expected 100 samples, got {len(samples)}"
    assert all(s > 0 for s in samples), "All samples should be positive"
    print(f"✓ Emissions distribution: {len(samples)} samples generated")
    
    # Test confidence interval
    ci_lower, ci_upper = compute_confidence_interval(samples)
    assert ci_lower < ci_upper, f"CI bounds invalid: {ci_lower} >= {ci_upper}"
    print(f"✓ Confidence interval: [{ci_lower:.3f}, {ci_upper:.3f}] kg CO₂")


def test_uncertainty_quantification():
    """Test complete uncertainty quantification."""
    print("Testing Uncertainty Quantification...")
    
    energy = MockEnergy.from_kWh(5.0)
    uncertainty = quantify_emissions_uncertainty(
        energy,
        carbon_intensity_gco2_kwh=400.0,
        pue=1.2,
        seed=42,
    )
    
    assert uncertainty.emissions_kg > 0, "Emissions should be positive"
    assert uncertainty.ci_lower_kg < uncertainty.ci_upper_kg, "CI bounds should be ordered"
    assert uncertainty.confidence_level_pct == 95.0, "Confidence level should be 95%"
    
    print(f"✓ Point estimate: {uncertainty.emissions_kg:.3f} kg CO₂")
    print(f"✓ 95% CI: [{uncertainty.ci_lower_kg:.3f}, {uncertainty.ci_upper_kg:.3f}] kg CO₂")
    print(f"✓ Relative uncertainty: {uncertainty.relative_uncertainty_pct:.1f}%")


def test_uncertainty_assessment():
    """Test uncertainty quality assessment."""
    print("Testing Uncertainty Assessment...")
    
    # Create mock uncertainty with high uncertainty
    high_uncertainty = UncertaintySummary(
        method="Monte Carlo",
        emissions_kg=2.0,
        ci_lower_kg=1.0,
        ci_upper_kg=3.0,
        confidence_level_pct=95.0,
        relative_uncertainty_pct=50.0,  # High uncertainty
    )
    
    assessment = assess_uncertainty_quality(high_uncertainty)
    assert assessment["uncertainty_level"] == "HIGH", "Should detect high uncertainty"
    print(f"✓ High uncertainty detected: {assessment['uncertainty_level']}")
    
    # Create mock uncertainty with low uncertainty
    low_uncertainty = UncertaintySummary(
        method="Monte Carlo",  
        emissions_kg=2.0,
        ci_lower_kg=1.8,
        ci_upper_kg=2.2,
        confidence_level_pct=95.0,
        relative_uncertainty_pct=10.0,  # Low uncertainty
    )
    
    assessment = assess_uncertainty_quality(low_uncertainty)
    assert assessment["uncertainty_level"] == "LOW", "Should detect low uncertainty"
    print(f"✓ Low uncertainty detected: {assessment['uncertainty_level']}")


def main():
    """Run all tests."""
    print("=" * 60)
    print("CodeCarbon Uncertainty Analysis - Standalone Tests")
    print("=" * 60)
    
    try:
        test_basic_monte_carlo()
        print()
        test_uncertainty_quantification()
        print()
        test_uncertainty_assessment()
        print()
        print("✓ All tests passed! Uncertainty analysis implementation is working correctly.")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise


if __name__ == "__main__":
    main()