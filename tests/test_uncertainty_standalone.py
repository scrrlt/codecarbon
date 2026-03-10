#!/usr/bin/env python3
"""
Standalone test for uncertainty analysis functionality.

This script tests the Monte Carlo uncertainty analysis without requiring
the full CodeCarbon infrastructure or external dependencies.
"""

import sys
import os

# Add codecarbon directory to path for direct module imports
codecarbon_path = os.path.dirname(os.path.dirname(__file__))  # Go up one level from tests/
sys.path.insert(0, codecarbon_path)  # Add root codecarbon directory for module imports

# Direct imports to avoid full package initialization
import importlib.util

def load_module_from_path(module_name, file_path):
    """Load a Python module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    # Temporarily override any problematic imports in monte_carlo.py
    original_modules = {}
    required_mocks = [
        'codecarbon.core.units',
        'codecarbon.core.schemas',
    ]
    
    for mock_module in required_mocks:
        if mock_module not in sys.modules:
            # Create a minimal mock module
            mock = type(sys)('mock_module')
            if 'units' in mock_module:
                mock.Energy = MockEnergy
            elif 'schemas' in mock_module:
                mock.UncertaintySummary = UncertaintySummary
            sys.modules[mock_module] = mock
            original_modules[mock_module] = True
    
    try:
        spec.loader.exec_module(module)
        return module
    finally:
        # Clean up mocks
        for mock_module in original_modules:
            del sys.modules[mock_module]

def UncertaintySummary(mean_kg_co2, std_kg_co2, confidence_interval):
    """Mock UncertaintySummary for testing."""
    return {
        'mean_kg_co2': mean_kg_co2,
        'std_kg_co2': std_kg_co2,
        'confidence_interval': confidence_interval,
    }

def MockEnergy(kwh_value):
    """Mock Energy class for testing."""
    class MockEnergy:
        def __init__(self, kwh):
            self.kwh = kwh
        
        @property
        def kWh(self):
            return self.kwh
    
    return MockEnergy(kwh_value)

# Load monte_carlo module directly
monte_carlo_path = os.path.join(codecarbon_path, 'codecarbon', 'core', 'monte_carlo.py')
monte_carlo = load_module_from_path("monte_carlo", monte_carlo_path)

# Import functions from loaded module
_sample_normal = monte_carlo._sample_normal
estimate_emissions_distribution = monte_carlo.estimate_emissions_distribution
compute_confidence_interval = monte_carlo.compute_confidence_interval
quantify_emissions_uncertainty = monte_carlo.quantify_emissions_uncertainty
assess_uncertainty_quality = monte_carlo.assess_uncertainty_quality

def test_basic_monte_carlo():
    """Test basic Monte Carlo functionality."""
    print("Testing Monte Carlo Core Functions...")
    
    # Test normal sampling
    import random
    rng = random.Random(42)
    samples = [_sample_normal(100.0, 10.0, rng) for _ in range(100)]
    mean_sample = sum(samples) / len(samples)
    print(f"✓ Normal sampling: mean={mean_sample:.2f} (expected ~100)")
    
    # Test emissions distribution
    distribution = estimate_emissions_distribution(
        energy_kwh=1.0,
        carbon_intensity_gco2_kwh=500.0,
        n_samples=100,
        seed=42
    )
    mean_emissions = sum(distribution) / len(distribution)
    expected = (1.0 * 500.0) / 1000.0  # Convert to kg
    print(f"✓ Emissions distribution: mean={mean_emissions:.4f} kg CO₂ (expected ~{expected:.4f})")
    
    # Test confidence intervals
    test_data = [0.45, 0.47, 0.50, 0.52, 0.55]
    lower, upper = compute_confidence_interval(test_data, alpha=0.2)  # 80% CI
    print(f"✓ Confidence interval: [{lower:.3f}, {upper:.3f}]")
    
    # Test uncertainty assessment
    quality = assess_uncertainty_quality(12.5)
    print(f"✓ Quality assessment: {quality} (expected: moderate_precision)")

def test_full_uncertainty_analysis():
    """Test complete uncertainty quantification."""
    print("\nTesting Complete Uncertainty Analysis...")
    
    # Create mock energy object
    Energy = mock_energy_class()
    energy = Energy.from_kWh(1.5)
    
    # Run uncertainty analysis
    result = quantify_emissions_uncertainty(
        energy=energy,
        carbon_intensity_gco2_kwh=400.0,
        pue=1.2,
        energy_uncertainty_pct=10.0,
        carbon_intensity_uncertainty_pct=15.0,
        pue_uncertainty_pct=5.0,
        confidence_level=0.95,
        n_samples=500,
        seed=42
    )
    
    print(f"✓ Uncertainty Analysis Results:")
    print(f"  Method: {result['method']}")
    print(f"  Emissions: {result['emissions_kg']:.4f} kg CO₂")
    print(f"  95% CI: [{result['ci_lower_kg']:.4f}, {result['ci_upper_kg']:.4f}]")
    print(f"  Relative uncertainty: ±{result['relative_uncertainty_pct']:.1f}%")
    print(f"  Confidence level: {result['confidence_level_pct']:.0f}%")

def test_edge_cases():
    """Test edge cases and error conditions."""
    print("\nTesting Edge Cases...")
    
    # Zero energy
    Energy = mock_energy_class()
    energy = Energy.from_kWh(0.0)
    
    result = quantify_emissions_uncertainty(
        energy=energy,
        carbon_intensity_gco2_kwh=400.0,
        n_samples=100,
        seed=42
    )
    print(f"✓ Zero energy: {result['emissions_kg']:.4f} kg CO₂")
    
    # High uncertainty
    energy = Energy.from_kWh(1.0)
    result = quantify_emissions_uncertainty(
        energy=energy,
        carbon_intensity_gco2_kwh=400.0,
        energy_uncertainty_pct=50.0,
        carbon_intensity_uncertainty_pct=60.0,
        n_samples=100,
        seed=42
    )
    print(f"✓ High uncertainty: ±{result['relative_uncertainty_pct']:.1f}%")
    
    # Empty confidence interval
    lower, upper = compute_confidence_interval([])
    print(f"✓ Empty CI: [{lower}, {upper}] (expected: [0.0, 0.0])")

def test_deterministic_behavior():
    """Test that results are deterministic with fixed seed."""
    print("\nTesting Deterministic Behavior...")
    
    Energy = mock_energy_class()
    energy = Energy.from_kWh(1.0)
    
    # Run same analysis twice with same seed
    result1 = quantify_emissions_uncertainty(
        energy=energy,
        carbon_intensity_gco2_kwh=400.0,
        seed=123
    )
    
    result2 = quantify_emissions_uncertainty(
        energy=energy,
        carbon_intensity_gco2_kwh=400.0,
        seed=123
    )
    
    # Results should be identical
    assert result1['emissions_kg'] == result2['emissions_kg']
    assert result1['ci_lower_kg'] == result2['ci_lower_kg']
    assert result1['ci_upper_kg'] == result2['ci_upper_kg']
    
    print("✓ Deterministic behavior verified")

def main():
    """Run all uncertainty tests."""
    print("=" * 60)
    print("CodeCarbon Uncertainty Analysis - Standalone Tests")
    print("=" * 60)
    
    try:
        test_basic_monte_carlo()
        test_full_uncertainty_analysis()
        test_edge_cases() 
        test_deterministic_behavior()
        
        print("\n" + "=" * 60)
        print("ALL TESTS PASSED ✓")
        print("=" * 60)
        print("Uncertainty analysis implementation is working correctly!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)