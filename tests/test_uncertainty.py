"""
Unit tests for Monte Carlo uncertainty analysis in CodeCarbon.

Tests the uncertainty quantification functionality including Monte Carlo
sampling, confidence interval calculation, and integration with emissions
tracking components.
"""

import unittest
from unittest.mock import Mock, patch

from codecarbon.core.monte_carlo import (
    UncertaintySummary,
    _sample_normal,
    assess_uncertainty_quality,
    compute_confidence_interval,
    estimate_emissions_distribution,
    quantify_emissions_uncertainty,
)
from codecarbon.core.uncertainty_emissions import UncertaintyAwareEmissions
from codecarbon.core.units import Energy
from codecarbon.external.geography import GeoMetadata
from codecarbon.input import DataSource
from codecarbon.output_methods.uncertainty_emissions_data import (
    UncertaintyAwareEmissionsData,
)


class TestMonteCarloCore(unittest.TestCase):
    """Test core Monte Carlo functions."""

    def test_sample_normal_deterministic(self):
        """Test that normal sampling is deterministic with fixed seed."""
        import random

        rng = random.Random(42)

        # Multiple samples with the same seed should be identical
        samples1 = [_sample_normal(100.0, 10.0, rng) for _ in range(10)]

        rng = random.Random(42)  # Reset with same seed
        samples2 = [_sample_normal(100.0, 10.0, rng) for _ in range(10)]

        self.assertEqual(samples1, samples2)

    def test_sample_normal_zero_sigma(self):
        """Test that zero standard deviation returns the mean."""
        import random

        rng = random.Random(42)

        result = _sample_normal(100.0, 0.0, rng)
        self.assertEqual(result, 100.0)

    def test_estimate_emissions_distribution_basic(self):
        """Test basic emissions distribution estimation."""
        samples = estimate_emissions_distribution(
            energy_kwh=1.0, carbon_intensity_gco2_kwh=500.0, n_samples=100, seed=42
        )

        self.assertEqual(len(samples), 100)
        self.assertTrue(
            all(s >= 0 for s in samples)
        )  # All emissions should be positive

        # Mean should be approximately energy * carbon_intensity / 1000
        mean_emissions = sum(samples) / len(samples)
        expected_mean = (1.0 * 500.0) / 1000.0  # Convert g to kg
        self.assertAlmostEqual(mean_emissions, expected_mean, delta=0.1)

    def test_compute_confidence_interval(self):
        """Test confidence interval calculation."""
        # Simple test data
        samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]

        lower, upper = compute_confidence_interval(samples, alpha=0.1)  # 90% CI

        self.assertLess(lower, upper)
        self.assertGreaterEqual(lower, min(samples))
        self.assertLessEqual(upper, max(samples))

    def test_compute_confidence_interval_empty(self):
        """Test confidence interval with empty samples."""
        lower, upper = compute_confidence_interval([])
        self.assertEqual(lower, 0.0)
        self.assertEqual(upper, 0.0)

    def test_quantify_emissions_uncertainty(self):
        """Test complete uncertainty quantification."""
        energy = Energy.from_energy(1.5)

        result = quantify_emissions_uncertainty(
            energy=energy,
            carbon_intensity_gco2_kwh=400.0,
            pue=1.2,
            n_samples=100,
            seed=42,
        )

        # Check that result is a proper UncertaintySummary
        self.assertIsInstance(result, UncertaintySummary)
        self.assertEqual(result.method, "monte_carlo")
        self.assertGreater(result.emissions_kg, 0)
        self.assertLessEqual(result.ci_lower_kg, result.emissions_kg)
        self.assertGreaterEqual(result.ci_upper_kg, result.emissions_kg)

    def test_assess_uncertainty_quality(self):
        """Test uncertainty quality assessment."""
        self.assertEqual(assess_uncertainty_quality(3.0), "high_precision")
        self.assertEqual(assess_uncertainty_quality(10.0), "moderate_precision")
        self.assertEqual(assess_uncertainty_quality(20.0), "low_precision")
        self.assertEqual(assess_uncertainty_quality(30.0), "very_low_precision")


class TestUncertaintyAwareEmissions(unittest.TestCase):
    """Test the uncertainty-aware emissions calculator."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_data_source = Mock(spec=DataSource)
        self.emissions_calc = UncertaintyAwareEmissions(
            data_source=self.mock_data_source,
            enable_uncertainty=True,
            uncertainty_seed=42,
        )

        # Mock geo metadata
        self.geo = GeoMetadata(
            country_name="Test Country", country_iso_code="TC", region="Test Region"
        )

    @patch(
        "codecarbon.core.uncertainty_emissions.UncertaintyAwareEmissions.get_private_infra_emissions"
    )
    def test_get_private_infra_emissions_with_uncertainty(self, mock_base_method):
        """Test private infrastructure emissions with uncertainty."""
        # Mock the base method
        mock_base_method.return_value = 0.5  # kg CO2

        # Mock data source for carbon intensity
        self.emissions_calc._data_source.get_global_energy_mix_data.return_value = {
            "TC": {"carbon_intensity": 400.0}
        }

        energy = Energy.from_energy(1.0)

        emissions_kg, uncertainty = (
            self.emissions_calc.get_private_infra_emissions_with_uncertainty(
                energy, self.geo
            )
        )

        self.assertEqual(emissions_kg, 0.5)
        self.assertIsNotNone(uncertainty)
        self.assertEqual(uncertainty.method, "monte_carlo")

    def test_uncertainty_disabled(self):
        """Test behavior when uncertainty analysis is disabled."""
        self.emissions_calc.enable_uncertainty = False

        with patch.object(
            self.emissions_calc, "get_private_infra_emissions", return_value=0.3
        ):
            energy = Energy.from_energy(1.0)
            emissions_kg, uncertainty = (
                self.emissions_calc.get_private_infra_emissions_with_uncertainty(
                    energy, self.geo
                )
            )

            self.assertEqual(emissions_kg, 0.3)
            self.assertIsNone(uncertainty)


class TestUncertaintyAwareEmissionsData(unittest.TestCase):
    """Test the enhanced emissions data structure."""

    def test_set_uncertainty_data(self):
        """Test setting uncertainty data on emissions object."""
        emissions_data = UncertaintyAwareEmissionsData(
            timestamp="2024-03-10T12:00:00",
            project_name="test",
            run_id="123",
            experiment_id="exp1",
            duration=60.0,
            emissions=0.5,
            emissions_rate=0.008333,
            cpu_power=100,
            gpu_power=0,
            ram_power=20,
            cpu_energy=1.0,
            gpu_energy=0.0,
            ram_energy=0.2,
            energy_consumed=1.2,
            water_consumed=0.0,
            country_name="Test Country",
            country_iso_code="TC",
            region="Test Region",
            cloud_provider="",
            cloud_region="",
            os="Linux",
            python_version="3.12",
            codecarbon_version="2.0",
            cpu_count=4,
            cpu_model="Test CPU",
            gpu_count=0,
            gpu_model="",
            longitude=0.0,
            latitude=0.0,
            ram_total_size=16.0,
            tracking_mode="machine",
        )

        # Create uncertainty summary
        uncertainty_summary = UncertaintySummary(
            method="monte_carlo",
            emissions_kg=0.5,
            ci_lower_kg=0.45,
            ci_upper_kg=0.55,
            confidence_level_pct=95.0,
            relative_uncertainty_pct=10.0,
        )

        emissions_data.set_uncertainty_data(uncertainty_summary)

        # Check that uncertainty fields are set
        self.assertTrue(emissions_data.uncertainty_enabled)
        self.assertEqual(emissions_data.uncertainty_method, "monte_carlo")
        self.assertEqual(emissions_data.emissions_ci_lower_kg, 0.45)
        self.assertEqual(emissions_data.emissions_ci_upper_kg, 0.55)
        self.assertEqual(emissions_data.uncertainty_quality, "moderate_precision")

    def test_format_uncertainty_summary(self):
        """Test uncertainty summary formatting."""
        emissions_data = UncertaintyAwareEmissionsData(
            **self._get_minimal_emissions_data()
        )

        # Test without uncertainty
        summary = emissions_data.format_uncertainty_summary()
        self.assertIn("no uncertainty analysis", summary)

        # Test with uncertainty
        uncertainty_summary = UncertaintySummary(
            method="monte_carlo",
            emissions_kg=0.5,
            ci_lower_kg=0.45,
            ci_upper_kg=0.55,
            confidence_level_pct=95.0,
            relative_uncertainty_pct=10.0,
        )

        emissions_data.set_uncertainty_data(uncertainty_summary)
        summary = emissions_data.format_uncertainty_summary()

        self.assertIn("0.5000 kg CO₂", summary)
        self.assertIn("[0.4500, 0.5500]", summary)
        self.assertIn("±10.0%", summary)

    def test_confidence_interval_bounds_verification(self):
        """Test that 95% CI bounds are correctly calculated at 2.5% and 97.5% percentiles."""
        # Create a large, well-controlled sample for precise percentile testing
        n_samples = 10000
        samples = list(range(n_samples))  # 0, 1, 2, ..., 9999

        # Calculate 95% CI (alpha = 0.05)
        lower, upper = compute_confidence_interval(samples, alpha=0.05)

        # For a uniform distribution of 10000 samples (0-9999):
        # 2.5th percentile should be around index 250 (value ~249)
        # 97.5th percentile should be around index 9750 (value ~9749)
        expected_lower = n_samples * 0.025  # 250
        expected_upper = n_samples * 0.975  # 9750

        # Allow small tolerance for quantile method differences
        self.assertAlmostEqual(lower, expected_lower, delta=50)
        self.assertAlmostEqual(upper, expected_upper, delta=50)

        # Verify bounds are distinct and properly ordered
        self.assertLess(lower, upper)
        self.assertGreater(upper - lower, n_samples * 0.9)  # Should span ~90% of range

    def _get_minimal_emissions_data(self) -> dict:
        """Helper to create minimal emissions data."""
        return {
            "timestamp": "2024-03-10T12:00:00",
            "project_name": "test",
            "run_id": "123",
            "experiment_id": "exp1",
            "duration": 60.0,
            "emissions": 0.5,
            "emissions_rate": 0.008333,
            "cpu_power": 100,
            "gpu_power": 0,
            "ram_power": 20,
            "cpu_energy": 1.0,
            "gpu_energy": 0.0,
            "ram_energy": 0.2,
            "energy_consumed": 1.2,
            "water_consumed": 0.0,
            "country_name": "Test Country",
            "country_iso_code": "TC",
            "region": "Test Region",
            "cloud_provider": "",
            "cloud_region": "",
            "os": "Linux",
            "python_version": "3.12",
            "codecarbon_version": "2.0",
            "cpu_count": 4,
            "cpu_model": "Test CPU",
            "gpu_count": 0,
            "gpu_model": "",
            "longitude": 0.0,
            "latitude": 0.0,
            "ram_total_size": 16.0,
            "tracking_mode": "machine",
        }


if __name__ == "__main__":
    unittest.main()
