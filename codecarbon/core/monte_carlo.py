"""
Monte Carlo uncertainty analysis for CodeCarbon emissions tracking.

This module provides uncertainty quantification capabilities for carbon emissions
calculations by incorporating measurement uncertainty, model uncertainty, and
data source uncertainty using Monte Carlo simulation methods.

SECURITY NOTICE
---------------
All functions in this module rely on Python's pseudo-random number generators
(random.random()) for performance in statistical simulations. They are suitable
for uncertainty analysis and confidence interval estimation but MUST NOT
be used for security-sensitive or cryptographic purposes.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass
from typing import Optional

from codecarbon.core.units import Energy
from codecarbon.external.logger import logger


@dataclass(frozen=True)
class UncertaintySummary:
    """Metadata describing Monte Carlo uncertainty analysis results.

    Note: Physical clamping constraints (PUE ≥ 1.0, energy ≥ 0) create
    truncated normal distributions which may introduce slight positive bias
    in the mean estimate for low-energy scenarios.
    """

    method: str
    emissions_kg: float
    ci_lower_kg: float
    ci_upper_kg: float
    confidence_level_pct: float
    relative_uncertainty_pct: float


def _sample_normal(mu: float, sigma: float, rng: random.Random) -> float:
    """
    Sample from normal distribution using Box-Muller transform.

    Uses non-cryptographic pseudo-random number generator for performance
    in Monte Carlo simulations. NOT suitable for security applications.

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

    Notes:
        Default uncertainty values are based on literature:
        - Energy measurement: ±10% (typical smart meter uncertainty)
        - Carbon intensity: ±15% (grid mix temporal variation)
        - PUE: ±5% (datacenter efficiency variance)

        For reliable confidence intervals, n_samples should be ≥ 100.
        Small sample sizes (< 30) may produce unreliable statistical estimates.

        Physical clamping (PUE ≥ 1.0, energy ≥ 0) creates truncated normal
        distributions which may introduce slight positive bias in low-energy scenarios.
    """
    rng = random.Random() if seed is None else random.Random(seed)  # nosec B311
    samples: list[float] = []

    # Convert percentage uncertainties to standard deviations
    # (assuming ±2σ bounds)
    energy_sigma = energy_kwh * (energy_uncertainty_pct / 100.0) / 2.0
    ci_sigma = (
        carbon_intensity_gco2_kwh * (carbon_intensity_uncertainty_pct / 100.0) / 2.0
    )
    pue_sigma = pue * (pue_uncertainty_pct / 100.0) / 2.0
    
    # Variance summation validation: warn for high uncertainties
    max_uncertainty = max(
        energy_uncertainty_pct, 
        carbon_intensity_uncertainty_pct, 
        pue_uncertainty_pct
    )
    if max_uncertainty > 50.0:
        logger.warning(
            f"High uncertainty detected ({max_uncertainty:.1f}%). "
            f"Normal distribution assumption may be invalid with heavy truncation at zero-boundary. "
            f"Consider reduced uncertainty bounds or alternative distributions."
        )

    for _ in range(max(1, n_samples)):
        # Sample uncertain parameters
        sampled_energy = max(0.0, _sample_normal(energy_kwh, energy_sigma, rng))
        sampled_intensity = max(
            0.0, _sample_normal(carbon_intensity_gco2_kwh, ci_sigma, rng)
        )
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

    Note:
        Sample sizes below 100 may produce statistically unreliable confidence intervals.
        Consider increasing n_samples for production uncertainty analysis.
    """
    if not samples:
        return (0.0, 0.0)

    # Performance optimization: use statistics.quantiles for large datasets
    n = len(samples)
    if n >= 100:
        try:
            # Use 40 quantiles for proper 95% CI bounds (1/0.025 = 40)
            # This ensures we get exact 2.5% and 97.5% percentiles
            n_quantiles = int(1.0 / (alpha / 2.0))  # For α=0.05: 1/0.025 = 40
            quantiles = statistics.quantiles(samples, n=n_quantiles, method="inclusive")
            # statistics.quantiles(n=40) returns 39 cut-points (n-1 values)
            # For 95% CI: index 0 = 2.5th percentile, index 38 = 97.5th percentile
            n_cuts = len(quantiles)  # This is n_quantiles - 1 = 39
            lower_idx = 0  # First cut-point is 2.5th percentile
            upper_idx = n_cuts - 1  # Last cut-point is 97.5th percentile
            return (quantiles[lower_idx], quantiles[upper_idx])
        except (AttributeError, ValueError):
            # Fall back to manual sorting for older Python or edge cases
            pass

    # Manual percentile calculation for small samples or fallback
    sorted_samples = sorted(samples)

    # Edge case: very small sample sizes may produce identical bounds
    if n < 10:
        # Log warning for STATISTICALLY INSIGNIFICANT results
        logger.warning(
            f"Small sample size (n={n}) may produce unreliable confidence intervals. "
            "Consider n_samples >= 100 for production use."
        )
        # Return min/max for very small samples
        return (sorted_samples[0], sorted_samples[-1])

    # Calculate percentile indices
    lower_idx = int((alpha / 2.0) * (n - 1))
    upper_idx = int((1 - alpha / 2.0) * (n - 1))

    # Ensure bounds are distinct for small samples
    if lower_idx == upper_idx:
        lower_idx = max(0, lower_idx - 1)
        upper_idx = min(n - 1, upper_idx + 1)

    # Floating point precision check for values
    ci_lower = sorted_samples[lower_idx]
    ci_upper = sorted_samples[upper_idx]
    
    # Check if bounds are numerically indistinguishable
    if math.isclose(ci_lower, ci_upper, rel_tol=1e-9, abs_tol=1e-12):
        logger.warning(
            f"Confidence interval bounds are numerically identical ({ci_lower:.12f}). "
            f"Relative uncertainty calculation may be misleading. "
            f"Consider increasing sample size or checking input variability."
        )

    return (ci_lower, ci_upper)


def quantify_emissions_uncertainty(
    energy: Energy,
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

    This is the main entry point for uncertainty quantification in CodeCarbon.

    Args:
        energy: Energy consumption measurement
        carbon_intensity_gco2_kwh: Carbon intensity in g CO₂/kWh
        pue: Power Usage Effectiveness (≥ 1.0 for physical data centers)
        energy_uncertainty_pct: Energy measurement uncertainty (%)
        carbon_intensity_uncertainty_pct: Carbon intensity uncertainty (%)
        pue_uncertainty_pct: PUE uncertainty (%)
        confidence_level: Confidence level for interval (0.95 = 95%)
        n_samples: Monte Carlo sample count
        seed: Random seed for reproducibility. Note: seed=0 is a valid deterministic
              seed that produces repeatable results. Use seed=None for non-deterministic
              random sampling.

    Returns:
        UncertaintySummary with point estimate and confidence bounds

    Note:
        PUE is clamped to ≥ 1.0 as physical data centers cannot achieve PUE < 1.0
        (would imply negative infrastructure power). Research setups with heat
        recovery may report "effective PUE" < 1.0 but this prevents negative
        carbon artifacts that appear as bugs to most users.

    Example:
        >>> energy = Energy.from_kWh(1.5)
        >>> uncertainty = quantify_emissions_uncertainty(
        ...     energy,
        ...     carbon_intensity_gco2_kwh=500.0,
        ...     pue=1.2
        ... )
        >>> f"Emissions: {uncertainty.emissions_kg:.3f} kg CO₂"
        >>> f"95% CI: [{uncertainty.ci_lower_kg:.3f}, {uncertainty.ci_upper_kg:.3f}] kg CO₂"
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
    relative_uncertainty_pct = 0.0
    if mean_emissions > 0:
        uncertainty_range = ci_upper - ci_lower
        relative_uncertainty_pct = (uncertainty_range / (2 * mean_emissions)) * 100.0

    return UncertaintySummary(
        method="monte_carlo",
        emissions_kg=mean_emissions,
        ci_lower_kg=max(0.0, ci_lower),
        ci_upper_kg=max(0.0, ci_upper),
        confidence_level_pct=confidence_level * 100.0,
        relative_uncertainty_pct=relative_uncertainty_pct,
    )


def assess_uncertainty_quality(relative_uncertainty_pct: float) -> str:
    """
    Provide qualitative assessment of uncertainty magnitude.

    Args:
        relative_uncertainty_pct: Relative uncertainty as percentage

    Returns:
        Quality assessment string
    """
    if relative_uncertainty_pct <= 5.0:
        return "high_precision"
    elif relative_uncertainty_pct <= 15.0:
        return "moderate_precision"
    elif relative_uncertainty_pct <= 25.0:
        return "low_precision"
    else:
        return "very_low_precision"
