#!/usr/bin/env python3
"""
Demonstration script for uncertainty-aware emissions tracking in CodeCarbon.

This script showcases the enhanced emissions tracker with Monte Carlo 
uncertainty analysis, demonstrating confidence intervals and precision 
assessments for carbon footprint measurements.
"""

import time
import numpy as np
from codecarbon.uncertainty_emissions_tracker import UncertaintyAwareEmissionsTracker


def simulate_compute_workload(duration_seconds: float, intensity: str = "medium") -> None:
    """
    Simulate a computational workload with varying intensity levels.
    
    Args:
        duration_seconds: How long to run the simulation
        intensity: 'low', 'medium', or 'high' computational intensity
    """
    print(f"Simulating {intensity} intensity workload for {duration_seconds:.1f} seconds...")
    
    # CPU-intensive work based on intensity level
    if intensity == "low":
        # Light computation
        for _ in range(int(duration_seconds * 100)):
            _ = sum(range(1000))
            time.sleep(0.01)
    elif intensity == "medium":
        # Medium computation with some array operations
        for _ in range(int(duration_seconds * 10)):
            arr = np.random.rand(1000, 100)
            _ = np.mean(arr @ arr.T)
            time.sleep(0.1)
    elif intensity == "high":
        # Heavy computation
        for _ in range(int(duration_seconds * 5)):
            arr = np.random.rand(2000, 500)
            _ = np.linalg.svd(arr @ arr.T, compute_uv=False)
            time.sleep(0.2)
    
    print(f"Completed {intensity} intensity simulation")


def demo_basic_uncertainty_tracking():
    """Demonstrate basic uncertainty-aware emissions tracking."""
    print("\n" + "="*60)
    print("DEMO 1: Basic Uncertainty-Aware Emissions Tracking")
    print("="*60)
    
    # Create uncertainty-aware tracker with default settings
    tracker = UncertaintyAwareEmissionsTracker(
        project_name="uncertainty_demo",
        experiment_name="basic_tracking",
        enable_uncertainty=True,
        energy_uncertainty_pct=10.0,  # ±10% energy measurement uncertainty
        carbon_intensity_uncertainty_pct=15.0,  # ±15% carbon intensity uncertainty
        pue_uncertainty_pct=5.0,  # ±5% PUE uncertainty
        uncertainty_confidence_level=0.95,  # 95% confidence intervals
        monte_carlo_samples=1000,  # 1000 MC samples for smooth distributions
        save_to_file=True,
        output_file="uncertainty_demo_basic.csv"
    )
    
    print("Starting emissions tracking with uncertainty analysis...")
    tracker.start()
    
    # Simulate some computational work
    simulate_compute_workload(5.0, "medium")
    
    # Stop tracking and get results
    emissions_data = tracker.stop()
    
    if hasattr(emissions_data, 'format_uncertainty_summary'):
        print("\nUncertainty Analysis Results:")
        print("-" * 40)
        print(emissions_data.format_uncertainty_summary())
    else:
        print(f"\nBasic Results: {emissions_data:.6f} kg CO₂")


def demo_precision_comparison():
    """Compare different precision levels by adjusting uncertainty parameters."""
    print("\n" + "="*60)
    print("DEMO 2: Precision Level Comparison")
    print("="*60)
    
    scenarios = [
        {
            "name": "High Precision (Lab Environment)",
            "energy_unc": 2.0,
            "carbon_unc": 5.0,
            "pue_unc": 1.0,
            "description": "Precise measurement equipment, stable grid"
        },
        {
            "name": "Moderate Precision (Typical Datacenter)",
            "energy_unc": 10.0,
            "carbon_unc": 15.0,
            "pue_unc": 5.0,
            "description": "Standard monitoring, typical grid variation"
        },
        {
            "name": "Low Precision (Edge/Mobile)",
            "energy_unc": 25.0,
            "carbon_unc": 30.0,
            "pue_unc": 15.0,
            "description": "Estimated values, high grid uncertainty"
        },
    ]
    
    for i, scenario in enumerate(scenarios):
        print(f"\nScenario {i+1}: {scenario['name']}")
        print(f"Description: {scenario['description']}")
        print("-" * 50)
        
        tracker = UncertaintyAwareEmissionsTracker(
            project_name="uncertainty_demo",
            experiment_name=f"precision_scenario_{i+1}",
            enable_uncertainty=True,
            energy_uncertainty_pct=scenario["energy_unc"],
            carbon_intensity_uncertainty_pct=scenario["carbon_unc"],
            pue_uncertainty_pct=scenario["pue_unc"],
            uncertainty_confidence_level=0.95,
            monte_carlo_samples=1000,
            save_to_file=False  # Don't save for this demo
        )
        
        tracker.start()
        simulate_compute_workload(3.0, "low")  # Standardized workload
        emissions_data = tracker.stop()
        
        if hasattr(emissions_data, 'format_uncertainty_summary'):
            print(emissions_data.format_uncertainty_summary())


def demo_confidence_levels():
    """Demonstrate different confidence level settings."""
    print("\n" + "="*60)
    print("DEMO 3: Different Confidence Levels")
    print("="*60)
    
    confidence_levels = [0.90, 0.95, 0.99]
    
    for confidence in confidence_levels:
        print(f"\n{confidence*100:.0f}% Confidence Level Analysis:")
        print("-" * 40)
        
        tracker = UncertaintyAwareEmissionsTracker(
            project_name="uncertainty_demo",
            experiment_name=f"confidence_{int(confidence*100)}",
            enable_uncertainty=True,
            uncertainty_confidence_level=confidence,
            monte_carlo_samples=1000,
            save_to_file=False
        )
        
        tracker.start()
        simulate_compute_workload(2.0, "medium")
        emissions_data = tracker.stop()
        
        if hasattr(emissions_data, 'format_uncertainty_summary'):
            print(emissions_data.format_uncertainty_summary())


def demo_uncertainty_disabled():
    """Show standard tracking without uncertainty for comparison."""
    print("\n" + "="*60)
    print("DEMO 4: Standard Tracking (No Uncertainty)")
    print("="*60)
    
    tracker = UncertaintyAwareEmissionsTracker(
        project_name="uncertainty_demo",
        experiment_name="no_uncertainty",
        enable_uncertainty=False,  # Disable uncertainty analysis
        save_to_file=False
    )
    
    print("Running standard emissions tracking (no uncertainty analysis)...")
    tracker.start()
    simulate_compute_workload(3.0, "medium")
    emissions_data = tracker.stop()
    
    if hasattr(emissions_data, 'format_uncertainty_summary'):
        print("\nStandard Results:")
        print("-" * 20)
        print(emissions_data.format_uncertainty_summary())
    else:
        print(f"\nStandard Results: {emissions_data:.6f} kg CO₂")


def main():
    """Run all uncertainty tracking demonstrations."""
    print("CodeCarbon Uncertainty-Aware Emissions Tracking Demo")
    print("=" * 60)
    print("This demo showcases Monte Carlo uncertainty analysis")
    print("for carbon emissions measurements with confidence intervals.")
    
    try:
        # Run demonstration scenarios
        demo_basic_uncertainty_tracking()
        demo_precision_comparison()
        demo_confidence_levels()
        demo_uncertainty_disabled()
        
        print("\n" + "="*60)
        print("DEMO COMPLETE")
        print("="*60)
        print("Key Insights:")
        print("• Uncertainty quantification provides confidence intervals")
        print("• Different environments have varying precision levels")
        print("• Higher confidence levels produce wider intervals")
        print("• Uncertainty analysis is optional and configurable")
        print("\nCheck 'uncertainty_demo_basic.csv' for detailed results.")
        
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install required packages: pip install numpy")
    except Exception as e:
        print(f"Demo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()