"""
Uncertainty-aware emissions tracker for CodeCarbon.

This module provides an enhanced emissions tracker that incorporates
Monte Carlo uncertainty analysis to provide confidence intervals
and precision assessments for carbon footprint measurements.
"""

import dataclasses
import time
from datetime import datetime
from typing import Optional

from codecarbon.core.uncertainty_emissions import UncertaintyAwareEmissions
from codecarbon.core.units import Energy
from codecarbon.emissions_tracker import BaseEmissionsTracker, _sentinel
from codecarbon.external.geography import CloudMetadata
from codecarbon.external.logger import logger
from codecarbon.input import DataSource
from codecarbon.output_methods.uncertainty_emissions_data import UncertaintyAwareEmissionsData


class UncertaintyAwareEmissionsTracker(BaseEmissionsTracker):
    """
    Enhanced emissions tracker with Monte Carlo uncertainty quantification.
    
    This tracker extends the base functionality to provide uncertainty
    analysis for emissions estimates, including confidence intervals
    and precision assessments.
    """

    def __init__(
        self,
        project_name: str = _sentinel,
        experiment_name: str = _sentinel,
        experiment_id: str = _sentinel,
        output_dir: str = _sentinel,
        output_file: str = _sentinel,
        save_to_file: bool = _sentinel,
        save_to_api: bool = _sentinel,
        save_to_logger: bool = _sentinel,
        logging_logger: object = _sentinel,
        api_call_interval: int = _sentinel,
        api_endpoint: str = _sentinel,
        api_key: str = _sentinel,
        measure_power_secs: int = _sentinel,
        tracking_mode: str = _sentinel,
        log_level: str = _sentinel,
        on_csv_write: str = _sentinel,
        logger_preamble: str = _sentinel,
        default_cpu_power: int = _sentinel,
        emissions_endpoint: str = _sentinel,
        experiment_config: dict = _sentinel,
        co2_signal_api_token: str = _sentinel,
        electricitymaps_api_token: str = _sentinel,
        # Uncertainty-specific parameters
        enable_uncertainty: bool = True,
        energy_uncertainty_pct: float = 10.0,
        carbon_intensity_uncertainty_pct: float = 15.0,
        pue_uncertainty_pct: float = 5.0,
        uncertainty_confidence_level: float = 0.95,
        monte_carlo_samples: int = 1000,
        uncertainty_seed: Optional[int] = 42,
    ):
        """
        Initialize uncertainty-aware emissions tracker.
        
        Args:
            (Standard CodeCarbon parameters follow base tracker)
            enable_uncertainty: Whether to perform uncertainty analysis
            energy_uncertainty_pct: Energy measurement uncertainty (%)
            carbon_intensity_uncertainty_pct: Carbon intensity data uncertainty (%)
            pue_uncertainty_pct: PUE uncertainty (%)
            uncertainty_confidence_level: Confidence level for intervals (0.95 = 95%)
            monte_carlo_samples: Number of Monte Carlo samples for analysis
            uncertainty_seed: Random seed for reproducible uncertainty analysis
        """
        
        # Initialize base tracker
        super().__init__(
            project_name=project_name,
            experiment_name=experiment_name,
            experiment_id=experiment_id,
            output_dir=output_dir,
            output_file=output_file,
            save_to_file=save_to_file,
            save_to_api=save_to_api,
            save_to_logger=save_to_logger,
            logging_logger=logging_logger,
            api_call_interval=api_call_interval,
            api_endpoint=api_endpoint,
            api_key=api_key,
            measure_power_secs=measure_power_secs,
            tracking_mode=tracking_mode,
            log_level=log_level,
            on_csv_write=on_csv_write,
            logger_preamble=logger_preamble,
            default_cpu_power=default_cpu_power,
            emissions_endpoint=emissions_endpoint,
            experiment_config=experiment_config,
            co2_signal_api_token=co2_signal_api_token,
            electricitymaps_api_token=electricitymaps_api_token,
        )
        
        # Store uncertainty configuration
        self.enable_uncertainty = enable_uncertainty
        self.energy_uncertainty_pct = energy_uncertainty_pct
        self.carbon_intensity_uncertainty_pct = carbon_intensity_uncertainty_pct
        self.pue_uncertainty_pct = pue_uncertainty_pct
        self.uncertainty_confidence_level = uncertainty_confidence_level
        self.monte_carlo_samples = monte_carlo_samples
        self.uncertainty_seed = uncertainty_seed
        
        # Replace standard emissions calculator with uncertainty-aware version
        data_source = DataSource()
        self._emissions = UncertaintyAwareEmissions(
            data_source=data_source,
            electricitymaps_api_token=self._electricitymaps_api_token,
            enable_uncertainty=enable_uncertainty,
            default_energy_uncertainty_pct=energy_uncertainty_pct,
            default_carbon_intensity_uncertainty_pct=carbon_intensity_uncertainty_pct,
            default_pue_uncertainty_pct=pue_uncertainty_pct,
            uncertainty_confidence_level=uncertainty_confidence_level,
            monte_carlo_samples=monte_carlo_samples,
            uncertainty_seed=uncertainty_seed,
        )
        
        # Track uncertainty analysis results
        self._last_uncertainty_summary = None

    def _prepare_emissions_data(self) -> UncertaintyAwareEmissionsData:
        """
        Prepare enhanced emissions data with uncertainty analysis.
        
        Uses composition over duplication by calling the base class method
        and then enhancing it with uncertainty-specific fields.
        
        Returns:
            UncertaintyAwareEmissionsData object with uncertainty metadata
        """
        # Call parent class method to get base emissions data
        base_emissions_data = super()._prepare_emissions_data()
        
        # Convert to uncertainty-aware version by copying all fields
        uncertainty_emissions_data = UncertaintyAwareEmissionsData(
            **dataclasses.asdict(base_emissions_data)
        )
        
        # Add uncertainty data if available
        if self._last_uncertainty_summary and self.enable_uncertainty:
            uncertainty_emissions_data.set_uncertainty_data(self._last_uncertainty_summary)
            uncertainty_emissions_data.energy_uncertainty_pct = self.energy_uncertainty_pct
            uncertainty_emissions_data.carbon_intensity_uncertainty_pct = self.carbon_intensity_uncertainty_pct
            uncertainty_emissions_data.pue_uncertainty_pct = self.pue_uncertainty_pct
            uncertainty_emissions_data.monte_carlo_samples = self.monte_carlo_samples
            uncertainty_emissions_data.uncertainty_seed = self.uncertainty_seed
            
            # Log uncertainty summary
            logger.info(uncertainty_emissions_data.format_uncertainty_summary())

        return uncertainty_emissions_data

    def _update_emissions(self) -> None:
        """
        Update emissions calculations with uncertainty analysis.
        
        This method extends the base class functionality by performing
        uncertainty-aware emissions calculation instead of point estimates only.
        """
        delta_energy = self._total_energy - self._last_energy_covered
        
        if delta_energy.kWh <= 0:
            self._last_uncertainty_summary = None
            return  # No new energy consumption to process
            
        cloud: CloudMetadata = self._get_cloud_metadata()
        
        if cloud.is_on_private_infra:
            # Private infrastructure with uncertainty
            delta_emissions, uncertainty_summary = (
                self._emissions.get_private_infra_emissions_with_uncertainty(
                    delta_energy,
                    self._geo,
                    pue=self._pue,
                    energy_uncertainty_pct=self.energy_uncertainty_pct,
                    carbon_intensity_uncertainty_pct=self.carbon_intensity_uncertainty_pct,
                    pue_uncertainty_pct=self.pue_uncertainty_pct,
                )
            )
        else:
            # Cloud infrastructure with uncertainty
            delta_emissions, uncertainty_summary = (
                self._emissions.get_cloud_emissions_with_uncertainty(
                    delta_energy,
                    cloud,
                    geo=self._geo,
                    pue=self._pue,
                    energy_uncertainty_pct=self.energy_uncertainty_pct,
                    carbon_intensity_uncertainty_pct=self.carbon_intensity_uncertainty_pct,
                    pue_uncertainty_pct=self.pue_uncertainty_pct,
                )
            )
        
        # Update total emissions
        self._total_emissions += delta_emissions
        self._last_energy_covered = self._total_energy
        
        # Store uncertainty results for reporting
        self._last_uncertainty_summary = uncertainty_summary
        
        if uncertainty_summary:
            logger.debug(
                f"Delta emissions: {delta_emissions:.4f} kg CO₂, "
                f"Uncertainty: ±{uncertainty_summary.relative_uncertainty_pct:.1f}%"
            )