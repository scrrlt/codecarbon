"""
Enhanced emissions calculations with uncertainty quantification.

This module extends CodeCarbon's emissions calculation capabilities with
Monte Carlo uncertainty analysis, providing confidence intervals and 
precision assessments for carbon footprint estimates.
"""

from typing import Optional

from codecarbon.core.emissions import Emissions
from codecarbon.core.monte_carlo import UncertaintySummary, quantify_emissions_uncertainty
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
        self.default_carbon_intensity_uncertainty_pct = default_carbon_intensity_uncertainty_pct
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
            
        # Get carbon intensity for uncertainty analysis
        carbon_intensity_gco2_kwh = self._get_carbon_intensity_for_geo(geo)
        
        # Use provided uncertainties or defaults
        energy_unc = energy_uncertainty_pct or self.default_energy_uncertainty_pct
        ci_unc = carbon_intensity_uncertainty_pct or self.default_carbon_intensity_uncertainty_pct
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
                f"Uncertainty analysis: {uncertainty_summary['emissions_kg']:.3f} kg CO₂ "
                f"(95% CI: [{uncertainty_summary['ci_lower_kg']:.3f}, "
                f"{uncertainty_summary['ci_upper_kg']:.3f}]), "
                f"relative uncertainty: {uncertainty_summary['relative_uncertainty_pct']:.1f}%"
            )
            
            return point_emissions_kg, uncertainty_summary
            
        except Exception as e:
            logger.warning(f"Uncertainty analysis failed: {e}. Returning point estimate only.")
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
            
        # Get carbon intensity for uncertainty analysis
        carbon_intensity_gco2_kwh = self._get_carbon_intensity_for_cloud(cloud, geo)
        
        # Cloud environments typically have higher PUE uncertainty
        # due to varying datacenter efficiency and location
        cloud_pue_uncertainty = (pue_uncertainty_pct or self.default_pue_uncertainty_pct) * 1.5
        
        # Use provided uncertainties or defaults
        energy_unc = energy_uncertainty_pct or self.default_energy_uncertainty_pct
        ci_unc = carbon_intensity_uncertainty_pct or self.default_carbon_intensity_uncertainty_pct
        
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
                f"Cloud uncertainty analysis: {uncertainty_summary['emissions_kg']:.3f} kg CO₂ "
                f"(95% CI: [{uncertainty_summary['ci_lower_kg']:.3f}, "
                f"{uncertainty_summary['ci_upper_kg']:.3f}])"
            )
            
            return point_emissions_kg, uncertainty_summary
            
        except Exception as e:
            logger.warning(f"Cloud uncertainty analysis failed: {e}. Returning point estimate only.")
            return point_emissions_kg, None

    def _get_carbon_intensity_for_geo(self, geo: GeoMetadata) -> float:
        """
        Extract carbon intensity value for geographic region.
        
        Args:
            geo: Geographic metadata
            
        Returns:
            Carbon intensity in g CO₂/kWh
        """
        try:
            # Check for regional data first
            if geo.region and geo.country_iso_code.upper() in ["USA", "CAN"]:
                country_data = self._data_source.get_country_emissions_data(
                    geo.country_iso_code.lower()
                )
                if geo.region in country_data:
                    # Convert from lbs/MWh to g/kWh if needed
                    emissions_per_kwh = country_data[geo.region].get("emissions", 0)
                    return emissions_per_kwh * 453.592  # lbs to grams conversion
                    
            # Fallback to country-level data
            energy_mix = self._data_source.get_global_energy_mix_data()
            if geo.country_iso_code in energy_mix:
                country_data = energy_mix[geo.country_iso_code]
                if "carbon_intensity" in country_data:
                    return country_data["carbon_intensity"]
                    
            # Ultimate fallback to world average
            carbon_intensity_per_source = self._data_source.get_carbon_intensity_per_source_data()
            return carbon_intensity_per_source.get("world_average", 475.0)  # g CO₂/kWh
            
        except Exception as e:
            logger.warning(f"Failed to get carbon intensity for {geo.country_name}: {e}")
            return 475.0  # World average fallback

    def _get_carbon_intensity_for_cloud(
        self, 
        cloud: CloudMetadata, 
        geo: Optional[GeoMetadata] = None
    ) -> float:
        """
        Extract carbon intensity value for cloud region.
        
        Args:
            cloud: Cloud metadata
            geo: Geographic metadata (fallback)
            
        Returns:
            Carbon intensity in g CO₂/kWh
        """
        try:
            # Get cloud-specific carbon intensity
            df = self._data_source.get_cloud_emissions_data()
            matches = df[
                (df["provider"] == cloud.provider) & (df["region"] == cloud.region)
            ]
            
            if len(matches) > 0:
                return matches["impact"].iloc[0]  # g CO₂/kWh
                
            # Fallback to geographic data
            if geo:
                return self._get_carbon_intensity_for_geo(geo)
                
            # Ultimate fallback
            carbon_intensity_per_source = self._data_source.get_carbon_intensity_per_source_data()
            return carbon_intensity_per_source.get("world_average", 475.0)
            
        except Exception as e:
            logger.warning(f"Failed to get cloud carbon intensity for {cloud.provider}/{cloud.region}: {e}")
            return 475.0  # World average fallback