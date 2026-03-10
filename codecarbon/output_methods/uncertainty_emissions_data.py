"""
Enhanced emissions data structures with uncertainty quantification.

This module extends the base EmissionsData structure to include uncertainty
metadata and confidence intervals from Monte Carlo analysis.
"""

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Optional

from codecarbon.core.monte_carlo import UncertaintySummary
from codecarbon.output_methods.emissions_data import EmissionsData


@dataclass
class UncertaintyAwareEmissionsData(EmissionsData):
    """
    Enhanced emissions data with uncertainty quantification.
    
    Extends the base EmissionsData to include confidence intervals
    and uncertainty metadata from Monte Carlo analysis.
    """
    
    # Uncertainty analysis results
    uncertainty_enabled: bool = False
    uncertainty_method: Optional[str] = None
    emissions_ci_lower_kg: Optional[float] = None
    emissions_ci_upper_kg: Optional[float] = None
    confidence_level_pct: Optional[float] = None
    relative_uncertainty_pct: Optional[float] = None
    uncertainty_quality: Optional[str] = None
    
    # Uncertainty input parameters (for audit trail)
    energy_uncertainty_pct: Optional[float] = None
    carbon_intensity_uncertainty_pct: Optional[float] = None
    pue_uncertainty_pct: Optional[float] = None
    monte_carlo_samples: Optional[int] = None
    uncertainty_seed: Optional[int] = None

    def set_uncertainty_data(self, uncertainty_summary: UncertaintySummary) -> None:
        """
        Populate uncertainty fields from Monte Carlo analysis results.
        
        Args:
            uncertainty_summary: Results from uncertainty quantification
        """
        self.uncertainty_enabled = True
        self.uncertainty_method = uncertainty_summary["method"]
        self.emissions_ci_lower_kg = uncertainty_summary["ci_lower_kg"]
        self.emissions_ci_upper_kg = uncertainty_summary["ci_upper_kg"]
        self.confidence_level_pct = uncertainty_summary["confidence_level_pct"]
        self.relative_uncertainty_pct = uncertainty_summary["relative_uncertainty_pct"]
        
        # Assess uncertainty quality
        if self.relative_uncertainty_pct is not None:
            if self.relative_uncertainty_pct <= 5.0:
                self.uncertainty_quality = "high_precision"
            elif self.relative_uncertainty_pct <= 15.0:
                self.uncertainty_quality = "moderate_precision"
            elif self.relative_uncertainty_pct <= 25.0:
                self.uncertainty_quality = "low_precision"
            else:
                self.uncertainty_quality = "very_low_precision"

    @property
    def values(self) -> OrderedDict:
        """Extended values property including uncertainty fields."""
        base_values = super().values
        
        # Add uncertainty fields to the ordered dict
        if self.uncertainty_enabled:
            uncertainty_fields = [
                ('uncertainty_enabled', self.uncertainty_enabled),
                ('uncertainty_method', self.uncertainty_method),
                ('emissions_ci_lower_kg', self.emissions_ci_lower_kg),
                ('emissions_ci_upper_kg', self.emissions_ci_upper_kg),
                ('confidence_level_pct', self.confidence_level_pct),
                ('relative_uncertainty_pct', self.relative_uncertainty_pct),
                ('uncertainty_quality', self.uncertainty_quality),
                ('energy_uncertainty_pct', self.energy_uncertainty_pct),
                ('carbon_intensity_uncertainty_pct', self.carbon_intensity_uncertainty_pct),
                ('pue_uncertainty_pct', self.pue_uncertainty_pct),
                ('monte_carlo_samples', self.monte_carlo_samples),
                ('uncertainty_seed', self.uncertainty_seed),
            ]
            
            # Insert uncertainty fields after the main emissions field
            updated_values = OrderedDict()
            for key, value in base_values.items():
                updated_values[key] = value
                if key == 'emissions_rate':  # Insert after emissions_rate
                    for unc_key, unc_value in uncertainty_fields:
                        updated_values[unc_key] = unc_value
                        
            return updated_values
        
        return base_values

    def format_uncertainty_summary(self) -> str:
        """
        Generate human-readable uncertainty summary.
        
        Returns:
            Formatted string with emissions and uncertainty information
        """
        if not self.uncertainty_enabled:
            return f"Emissions: {self.emissions:.4f} kg CO₂ (no uncertainty analysis)"
            
        ci_lower = self.emissions_ci_lower_kg or 0.0
        ci_upper = self.emissions_ci_upper_kg or 0.0
        confidence = self.confidence_level_pct or 95.0
        rel_unc = self.relative_uncertainty_pct or 0.0
        quality = self.uncertainty_quality or "unknown"
        
        summary = (
            f"Emissions: {self.emissions:.4f} kg CO₂\n"
            f"{confidence:.0f}% Confidence Interval: [{ci_lower:.4f}, {ci_upper:.4f}] kg CO₂\n"
            f"Relative Uncertainty: ±{rel_unc:.1f}% ({quality.replace('_', ' ')})"
        )
        
        return summary

    def to_uncertainty_dict(self) -> dict:
        """
        Extract uncertainty-specific fields as a dictionary.
        
        Returns:
            Dictionary containing only uncertainty metadata
        """
        if not self.uncertainty_enabled:
            return {"uncertainty_enabled": False}
            
        return {
            "uncertainty_enabled": self.uncertainty_enabled,
            "method": self.uncertainty_method,
            "emissions_kg": self.emissions,
            "ci_lower_kg": self.emissions_ci_lower_kg,
            "ci_upper_kg": self.emissions_ci_upper_kg,
            "confidence_level_pct": self.confidence_level_pct,
            "relative_uncertainty_pct": self.relative_uncertainty_pct,
            "quality_assessment": self.uncertainty_quality,
            "parameters": {
                "energy_uncertainty_pct": self.energy_uncertainty_pct,
                "carbon_intensity_uncertainty_pct": self.carbon_intensity_uncertainty_pct,
                "pue_uncertainty_pct": self.pue_uncertainty_pct,
                "monte_carlo_samples": self.monte_carlo_samples,
                "uncertainty_seed": self.uncertainty_seed,
            }
        }

    def toJSON(self):
        """Enhanced JSON serialization including uncertainty data."""
        return json.dumps(
            self, 
            default=lambda o: o.__dict__, 
            sort_keys=True, 
            indent=4
        )


@dataclass
class UncertaintyAwareTaskEmissionsData:
    """
    Task-level emissions data with uncertainty quantification.
    
    Similar to UncertaintyAwareEmissionsData but for individual tasks
    within a larger tracking experiment.
    """
    
    # Base task fields (from TaskEmissionsData)
    task_name: str
    timestamp: str
    project_name: str
    run_id: str
    duration: float
    emissions: float
    emissions_rate: float
    cpu_power: float
    gpu_power: float
    ram_power: float
    cpu_energy: float
    gpu_energy: float
    ram_energy: float
    energy_consumed: float
    water_consumed: float
    country_name: str
    country_iso_code: str
    region: str
    cloud_provider: str
    cloud_region: str
    os: str
    python_version: str
    codecarbon_version: str
    cpu_count: float
    cpu_model: str
    gpu_count: float
    gpu_model: str
    longitude: float
    latitude: float
    ram_total_size: float
    tracking_mode: str
    
    # Uncertainty fields
    uncertainty_enabled: bool = False
    uncertainty_method: Optional[str] = None
    emissions_ci_lower_kg: Optional[float] = None
    emissions_ci_upper_kg: Optional[float] = None
    confidence_level_pct: Optional[float] = None
    relative_uncertainty_pct: Optional[float] = None
    uncertainty_quality: Optional[str] = None

    def set_uncertainty_data(self, uncertainty_summary: UncertaintySummary) -> None:
        """Populate uncertainty fields from analysis results."""
        self.uncertainty_enabled = True
        self.uncertainty_method = uncertainty_summary["method"]
        self.emissions_ci_lower_kg = uncertainty_summary["ci_lower_kg"]
        self.emissions_ci_upper_kg = uncertainty_summary["ci_upper_kg"]
        self.confidence_level_pct = uncertainty_summary["confidence_level_pct"]
        self.relative_uncertainty_pct = uncertainty_summary["relative_uncertainty_pct"]
        
        # Quality assessment
        if self.relative_uncertainty_pct is not None:
            if self.relative_uncertainty_pct <= 5.0:
                self.uncertainty_quality = "high_precision"
            elif self.relative_uncertainty_pct <= 15.0:
                self.uncertainty_quality = "moderate_precision"
            elif self.relative_uncertainty_pct <= 25.0:
                self.uncertainty_quality = "low_precision"
            else:
                self.uncertainty_quality = "very_low_precision"