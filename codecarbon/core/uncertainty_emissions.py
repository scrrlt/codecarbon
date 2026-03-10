"""
Enhanced emissions calculations with uncertainty quantification.

This module extends CodeCarbon's emissions calculation capabilities with
Monte Carlo uncertainty analysis, providing confidence intervals and
precision assessments for carbon footprint estimates.
"""

import math
from typing import Optional

from codecarbon.core.emissions import Emissions
from codecarbon.core.monte_carlo import (
    UncertaintySummary,
    quantify_emissions_uncertainty,
)
from codecarbon.core.units import Energy
from codecarbon.external.geography import CloudMetadata, GeoMetadata
from codecarbon.external.logger import logger
from codecarbon.input import DataSource


class UncertaintyAwareEmissions(Emissions):
    """
    Enhanced Emissions class with Monte Carlo uncertainty quantification.

    Extends the base Emissions class to provide uncertainty-aware calculations
    that return both point estimates and confidence intervals for emissions.
    """

    def __init__(
        self,
        data_source: DataSource,
        electricitymaps_api_token: Optional[str] = None,
        enable_uncertainty: bool = True,
        default_energy_uncertainty_pct: float = 10.0,
        default_carbon_intensity_uncertainty_pct: float = 15.0,
        default_pue_uncertainty_pct: float = 5.0,
        uncertainty_confidence_level: float = 0.95,
        monte_carlo_samples: int = 1000,
        uncertainty_seed: Optional[int] = 42,
    ):
        """
        Initialize uncertainty-aware emissions calculator.

        Args:
            data_source: CodeCarbon data source instance
            electricitymaps_api_token: ElectricityMaps API token
            enable_uncertainty: Whether to compute uncertainty analysis
            default_energy_uncertainty_pct: Default energy measurement uncertainty (%)
            default_carbon_intensity_uncertainty_pct: Default carbon intensity uncertainty (%)
            default_pue_uncertainty_pct: Default PUE uncertainty (%)
            uncertainty_confidence_level: Confidence level for intervals (0.95 = 95%)
            monte_carlo_samples: Number of Monte Carlo samples
            uncertainty_seed: Random seed for reproducible uncertainty analysis
        """
        super().__init__(data_source, electricitymaps_api_token)

        self.enable_uncertainty = enable_uncertainty
        self.default_energy_uncertainty_pct = default_energy_uncertainty_pct
        self.default_carbon_intensity_uncertainty_pct = (
            default_carbon_intensity_uncertainty_pct
        )
        self.default_pue_uncertainty_pct = default_pue_uncertainty_pct
        self.uncertainty_confidence_level = uncertainty_confidence_level
        self.monte_carlo_samples = monte_carlo_samples
        self.uncertainty_seed = uncertainty_seed

    def get_private_infra_emissions_with_uncertainty(
        self,
        energy: Energy,
        geo: GeoMetadata,
        pue: float = 1.0,
        energy_uncertainty_pct: Optional[float] = None,
        carbon_intensity_uncertainty_pct: Optional[float] = None,
        pue_uncertainty_pct: Optional[float] = None,
    ) -> tuple[float, Optional[UncertaintySummary]]:
        """
        Compute emissions for private infrastructure with uncertainty analysis.

        Args:
            energy: Energy consumption measurement
            geo: Geographic metadata
            pue: Power Usage Effectiveness
            energy_uncertainty_pct: Energy measurement uncertainty override
            carbon_intensity_uncertainty_pct: Carbon intensity uncertainty override
            pue_uncertainty_pct: PUE uncertainty override

        Returns:
            Tuple of (emissions_kg, uncertainty_summary)
            uncertainty_summary is None if uncertainty analysis is disabled
        """
        # Get point estimate using parent class
        point_emissions_kg = self.get_private_infra_emissions(energy, geo)

        if not self.enable_uncertainty:
            return point_emissions_kg, None

        # Performance consideration: warn for large sample sizes
        if self.monte_carlo_samples > 10000:
            logger.warning(
                f"Large sample size ({self.monte_carlo_samples}) may cause performance issues. "
                "Consider reducing for high-frequency tracking."
            )

        # Use existing base class methods to get carbon intensity
        try:
            carbon_intensity_gco2_kwh = self._extract_carbon_intensity_from_emissions(
                point_emissions_kg, energy.kWh, pue
            )
        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Failed to extract carbon intensity: {e}")
            return point_emissions_kg, None

        # Use provided uncertainties or defaults
        energy_unc = energy_uncertainty_pct or self.default_energy_uncertainty_pct
        ci_unc = (
            carbon_intensity_uncertainty_pct
            or self.default_carbon_intensity_uncertainty_pct
        )
        pue_unc = pue_uncertainty_pct or self.default_pue_uncertainty_pct

        try:
            uncertainty_summary = quantify_emissions_uncertainty(
                energy=energy,
                carbon_intensity_gco2_kwh=carbon_intensity_gco2_kwh,
                pue=pue,
                energy_uncertainty_pct=energy_unc,
                carbon_intensity_uncertainty_pct=ci_unc,
                pue_uncertainty_pct=pue_unc,
                confidence_level=self.uncertainty_confidence_level,
                n_samples=self.monte_carlo_samples,
                seed=self.uncertainty_seed,
            )

            logger.debug(
                f"Uncertainty analysis: {uncertainty_summary.emissions_kg:.3f} kg CO₂ "
                f"(95% CI: [{uncertainty_summary.ci_lower_kg:.3f}, "
                f"{uncertainty_summary.ci_upper_kg:.3f}]), "
                f"relative uncertainty: {uncertainty_summary.relative_uncertainty_pct:.1f}%"
            )

            return point_emissions_kg, uncertainty_summary

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid parameters for uncertainty analysis: {e}")
            return point_emissions_kg, None
        except Exception as e:
            logger.warning(
                f"Unexpected error in uncertainty analysis: {e}. Returning point estimate only."
            )
            return point_emissions_kg, None

    def get_cloud_emissions_with_uncertainty(
        self,
        energy: Energy,
        cloud: CloudMetadata,
        geo: Optional[GeoMetadata] = None,
        pue: float = 1.0,
        energy_uncertainty_pct: Optional[float] = None,
        carbon_intensity_uncertainty_pct: Optional[float] = None,
        pue_uncertainty_pct: Optional[float] = None,
    ) -> tuple[float, Optional[UncertaintySummary]]:
        """
        Compute emissions for cloud infrastructure with uncertainty analysis.

        Args:
            energy: Energy consumption measurement
            cloud: Cloud metadata (provider, region)
            geo: Geographic metadata (fallback)
            pue: Power Usage Effectiveness
            energy_uncertainty_pct: Energy measurement uncertainty override
            carbon_intensity_uncertainty_pct: Carbon intensity uncertainty override
            pue_uncertainty_pct: PUE uncertainty override

        Returns:
            Tuple of (emissions_kg, uncertainty_summary)
        """
        # Get point estimate using parent class
        point_emissions_kg = self.get_cloud_emissions(energy, cloud, geo)

        if not self.enable_uncertainty:
            return point_emissions_kg, None

        # Performance consideration: warn for large sample sizes
        if self.monte_carlo_samples > 10000:
            logger.warning(
                f"Large sample size ({self.monte_carlo_samples}) may cause performance issues. "
                "Consider reducing for high-frequency tracking."
            )

        # Use existing base class methods to get carbon intensity
        try:
            carbon_intensity_gco2_kwh = self._extract_carbon_intensity_from_emissions(
                point_emissions_kg, energy.kWh, pue
            )
        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"Failed to extract carbon intensity: {e}")
            return point_emissions_kg, None

        # Cloud environments typically have higher PUE uncertainty
        # due to varying datacenter efficiency and location
        cloud_pue_uncertainty = (
            pue_uncertainty_pct or self.default_pue_uncertainty_pct
        ) * 1.5

        # Use provided uncertainties or defaults
        energy_unc = energy_uncertainty_pct or self.default_energy_uncertainty_pct
        ci_unc = (
            carbon_intensity_uncertainty_pct
            or self.default_carbon_intensity_uncertainty_pct
        )

        try:
            uncertainty_summary = quantify_emissions_uncertainty(
                energy=energy,
                carbon_intensity_gco2_kwh=carbon_intensity_gco2_kwh,
                pue=pue,
                energy_uncertainty_pct=energy_unc,
                carbon_intensity_uncertainty_pct=ci_unc,
                pue_uncertainty_pct=cloud_pue_uncertainty,
                confidence_level=self.uncertainty_confidence_level,
                n_samples=self.monte_carlo_samples,
                seed=self.uncertainty_seed,
            )

            logger.debug(
                f"Cloud uncertainty analysis: {uncertainty_summary.emissions_kg:.3f} kg CO₂ "
                f"(95% CI: [{uncertainty_summary.ci_lower_kg:.3f}, "
                f"{uncertainty_summary.ci_upper_kg:.3f}])"
            )

            return point_emissions_kg, uncertainty_summary

        except (ValueError, TypeError) as e:
            logger.error(f"Invalid parameters for cloud uncertainty analysis: {e}")
            return point_emissions_kg, None
        except Exception as e:
            logger.warning(
                f"Unexpected error in cloud uncertainty analysis: {e}. Returning point estimate only."
            )
            return point_emissions_kg, None

    def _extract_carbon_intensity_from_emissions(
        self, emissions_kg: float, energy_kwh: float, pue: float = 1.0
    ) -> float:
        """
        Extract carbon intensity from existing emissions calculation.

        This method leverages the existing calculation by reverse-engineering
        the carbon intensity from the emissions and energy values, avoiding
        duplication of the complex lookup logic in the base class.

        Args:
            emissions_kg: Calculated emissions in kg CO₂
            energy_kwh: Energy consumption in kWh
            pue: Power Usage Effectiveness

        Returns:
            Carbon intensity in g CO₂/kWh

        Raises:
            ValueError: If energy is zero or calculation is invalid
            ZeroDivisionError: If energy or PUE is zero
        """
        # Guard against NaN/Infinity inputs
        if (
            not math.isfinite(energy_kwh)
            or not math.isfinite(emissions_kg)
            or not math.isfinite(pue)
        ):
            logger.warning(
                "Non-finite input detected (energy_kwh=%s, emissions_kg=%s, pue=%s). "
                "Using world average fallback.",
                energy_kwh,
                emissions_kg,
                pue,
            )
            try:
                carbon_intensity_per_source = (
                    self._data_source.get_carbon_intensity_per_source_data()
                )
                return carbon_intensity_per_source.get("world_average", 475.0)
            except Exception:
                return 475.0

        if energy_kwh <= 1e-6:  # Below 1 milliwatt-hour threshold
            logger.warning(
                f"Energy consumption too small for reliable reverse calculation: {energy_kwh} kWh. "
                "Using world average fallback to prevent floating-point overflow."
            )
            try:
                carbon_intensity_per_source = (
                    self._data_source.get_carbon_intensity_per_source_data()
                )
                return carbon_intensity_per_source.get("world_average", 475.0)
            except Exception:
                return 475.0

        if pue <= 0:
            raise ZeroDivisionError(f"PUE must be positive, got {pue}")

        # Reverse-engineer carbon intensity from emissions calculation
        # emissions = energy * pue * carbon_intensity / 1000  (convert g to kg)
        # Therefore: carbon_intensity = emissions * 1000 / (energy * pue)
        carbon_intensity_gco2_kwh = (emissions_kg * 1000) / (energy_kwh * pue)

        # Guard against non-finite result from calculation
        if not math.isfinite(carbon_intensity_gco2_kwh):
            logger.warning(
                "Calculated carbon intensity is non-finite. Using world average fallback."
            )
            try:
                carbon_intensity_per_source = (
                    self._data_source.get_carbon_intensity_per_source_data()
                )
                return carbon_intensity_per_source.get("world_average", 475.0)
            except Exception:
                return 475.0

        if carbon_intensity_gco2_kwh < 0 or carbon_intensity_gco2_kwh > 2000:
            logger.warning(
                f"Calculated carbon intensity ({carbon_intensity_gco2_kwh:.1f} g CO₂/kWh) "
                "seems unrealistic. Using world average fallback."
            )
            # Use data source world average instead of hardcoded value
            try:
                carbon_intensity_per_source = (
                    self._data_source.get_carbon_intensity_per_source_data()
                )
                world_average = carbon_intensity_per_source.get("world_average", 475.0)
                return world_average
            except Exception as e:
                logger.warning(
                    f"Data source unavailable for world average ({e}). "
                    "Using ultimate fallback of 475.0 g CO₂/kWh. "
                    "This may indicate missing or corrupted library data files."
                )
                return 475.0

        return carbon_intensity_gco2_kwh
