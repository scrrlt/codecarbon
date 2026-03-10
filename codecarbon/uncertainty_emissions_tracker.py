"""
Uncertainty-aware emissions tracker for CodeCarbon.

This module provides an enhanced emissions tracker that incorporates
Monte Carlo uncertainty analysis to provide confidence intervals
and precision assessments for carbon footprint measurements.
"""

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
        
        Returns:
            UncertaintyAwareEmissionsData object with uncertainty metadata
        """
        self._update_emissions_with_uncertainty()
        cloud: CloudMetadata = self._get_cloud_metadata()
        duration = time.perf_counter() - self._start_time

        emissions = self._total_emissions
        
        # Calculate average power values (same as base tracker)
        avg_cpu_power = (
            self._cpu_power_sum / self._power_measurement_count
            if self._power_measurement_count > 0
            else self._cpu_power.W
        )
        avg_gpu_power = (
            self._gpu_power_sum / self._power_measurement_count
            if self._power_measurement_count > 0
            else self._gpu_power.W
        )
        avg_ram_power = (
            self._ram_power_sum / self._power_measurement_count
            if self._power_measurement_count > 0
            else self._ram_power.W
        )

        # Get geographic information (same logic as base tracker)
        if cloud.is_on_private_infra:
            country_name = self._geo.country_name
            country_iso_code = self._geo.country_iso_code
            region = self._geo.region
            on_cloud = "N"
            cloud_provider = ""
            cloud_region = ""
        else:
            try:
                country_name = self._emissions.get_cloud_country_name(cloud)
            except ValueError:
                country_name = self._geo.country_name
            
            try:
                country_iso_code = self._emissions.get_cloud_country_iso_code(cloud)
            except ValueError:
                country_iso_code = self._geo.country_iso_code
                
            try:
                region = self._emissions.get_cloud_geo_region(cloud)
            except ValueError:
                region = self._geo.region

            on_cloud = "Y"
            cloud_provider = cloud.provider
            cloud_region = cloud.region

        # Create enhanced emissions data object
        emissions_data = UncertaintyAwareEmissionsData(
            timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            project_name=self._project_name,
            run_id=str(self.run_id),
            experiment_id=str(self._experiment_id),
            duration=duration,
            emissions=emissions,
            emissions_rate=emissions / duration if duration > 0 else 0,
            cpu_utilization_percent=(
                sum(self._cpu_utilization_history) / len(self._cpu_utilization_history)
                if self._cpu_utilization_history
                else 0
            ),
            gpu_utilization_percent=(
                sum(self._gpu_utilization_history) / len(self._gpu_utilization_history)
                if self._gpu_utilization_history
                else 0
            ),
            ram_utilization_percent=(
                sum(self._ram_utilization_history) / len(self._ram_utilization_history)
                if self._ram_utilization_history
                else 0
            ),
            ram_used_gb=(
                sum(self._ram_used_history) / len(self._ram_used_history)
                if self._ram_used_history
                else 0
            ),
            cpu_power=avg_cpu_power,
            gpu_power=avg_gpu_power,
            ram_power=avg_ram_power,
            cpu_energy=self._total_cpu_energy.kWh,
            gpu_energy=self._total_gpu_energy.kWh,
            ram_energy=self._total_ram_energy.kWh,
            energy_consumed=self._total_energy.kWh,
            water_consumed=self._total_water.litres,
            country_name=country_name,
            country_iso_code=country_iso_code,
            region=region,
            on_cloud=on_cloud,
            cloud_provider=cloud_provider,
            cloud_region=cloud_region,
            os=self._conf.get("os"),
            python_version=self._conf.get("python_version"),
            codecarbon_version=self._conf.get("codecarbon_version"),
            gpu_count=self._conf.get("gpu_count", 0),
            gpu_model=self._conf.get("gpu_model", ""),
            cpu_count=self._conf.get("cpu_count"),
            cpu_model=self._conf.get("cpu_model"),
            longitude=self._conf.get("longitude"),
            latitude=self._conf.get("latitude"),
            ram_total_size=self._conf.get("ram_total_size"),
            tracking_mode=self._conf.get("tracking_mode"),
            pue=self._pue,
            wue=self._wue,
        )

        # Add uncertainty data if available
        if self._last_uncertainty_summary and self.enable_uncertainty:
            emissions_data.set_uncertainty_data(self._last_uncertainty_summary)
            emissions_data.energy_uncertainty_pct = self.energy_uncertainty_pct
            emissions_data.carbon_intensity_uncertainty_pct = self.carbon_intensity_uncertainty_pct
            emissions_data.pue_uncertainty_pct = self.pue_uncertainty_pct
            emissions_data.monte_carlo_samples = self.monte_carlo_samples
            emissions_data.uncertainty_seed = self.uncertainty_seed
            
            # Log uncertainty summary
            logger.info(emissions_data.format_uncertainty_summary())

        return emissions_data

    def _update_emissions_with_uncertainty(self) -> None:
        """
        Update emissions calculations with uncertainty analysis.
        
        This method performs the core uncertainty-aware emissions calculation,
        replacing the base tracker's _update_emissions method.
        """
        delta_energy = self._total_energy - self._last_energy_covered
        
        if delta_energy.kWh <= 0:
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
                f"Uncertainty: ±{uncertainty_summary['relative_uncertainty_pct']:.1f}%"
            )