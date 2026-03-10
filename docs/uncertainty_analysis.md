# Uncertainty-Aware Emissions Tracking

CodeCarbon now includes advanced uncertainty quantification capabilities using Monte Carlo analysis to provide confidence intervals and precision assessments for carbon emissions measurements.

## Overview

Traditional emissions tracking provides point estimates, but real-world measurements involve uncertainty from multiple sources:

- **Energy Measurement Uncertainty**: ±5-25% depending on monitoring infrastructure
- **Carbon Intensity Uncertainty**: ±10-30% due to grid mix temporal variation
- **PUE Uncertainty**: ±3-15% from datacenter efficiency estimates
- **Model Uncertainty**: Inherent limitations in emissions calculation methods

The uncertainty-aware tracker quantifies these sources to provide **confidence intervals** instead of just point estimates.

## Key Features

### Monte Carlo Uncertainty Analysis
- Uses 1000+ Monte Carlo samples for robust statistical analysis
- Incorporates multiple uncertainty sources simultaneously
- Provides configurable confidence levels (90%, 95%, 99%)

### Precision Assessment
- Automatic quality classification: `high_precision`, `moderate_precision`, `low_precision`, `very_low_precision`
- Relative uncertainty percentages for easy interpretation
- Precision-based decision support for carbon accounting

### Backward Compatibility
- Drop-in replacement for existing `EmissionsTracker`
- Uncertainty analysis can be enabled/disabled
- Existing outputs remain unchanged when uncertainty is disabled

## Quick Start

### Basic Usage

```python
from codecarbon.uncertainty_emissions_tracker import UncertaintyAwareEmissionsTracker

# Create uncertainty-aware tracker
tracker = UncertaintyAwareEmissionsTracker(
    project_name="my_project",
    enable_uncertainty=True,
    energy_uncertainty_pct=10.0,        # ±10% energy measurement uncertainty
    carbon_intensity_uncertainty_pct=15.0,  # ±15% carbon intensity uncertainty
    pue_uncertainty_pct=5.0,            # ±5% PUE uncertainty
    uncertainty_confidence_level=0.95,   # 95% confidence intervals
)

tracker.start()

# Your computational work here
import time
time.sleep(10)  # Simulate work

emissions_data = tracker.stop()

# Print uncertainty summary
print(emissions_data.format_uncertainty_summary())
```

Output:
```
Emissions: 0.0045 kg CO₂
95% Confidence Interval: [0.0039, 0.0052] kg CO₂
Relative Uncertainty: ±14.4% (moderate precision)
```

### Advanced Configuration

```python
tracker = UncertaintyAwareEmissionsTracker(
    project_name="high_precision_experiment",
    
    # Enable uncertainty analysis
    enable_uncertainty=True,
    
    # Customize uncertainty parameters for your environment
    energy_uncertainty_pct=2.0,         # Lab environment: precise power meters
    carbon_intensity_uncertainty_pct=8.0,   # Stable grid with good data
    pue_uncertainty_pct=1.5,            # Well-characterized datacenter
    
    # Statistical configuration
    uncertainty_confidence_level=0.99,   # 99% confidence (wider intervals)
    monte_carlo_samples=5000,           # More samples for smoother estimates
    uncertainty_seed=None,              # Non-deterministic (None) vs deterministic (int)
    
    # Standard CodeCarbon options
    save_to_file=True,
    output_file="precise_emissions.csv"
)
```

## Environment-Specific Guidelines

### High Precision Environments
**Use Case**: Research labs, controlled experiments, compliance reporting

```python
tracker = UncertaintyAwareEmissionsTracker(
    enable_uncertainty=True,
    energy_uncertainty_pct=2.0,        # Calibrated power meters
    carbon_intensity_uncertainty_pct=5.0,   # Real-time grid API
    pue_uncertainty_pct=1.0,           # Measured datacenter efficiency
)
```
**Expected Result**: ±3-8% relative uncertainty (high precision)

### Standard Datacenter Environments  
**Use Case**: Cloud deployments, typical enterprise infrastructure

```python
tracker = UncertaintyAwareEmissionsTracker(
    enable_uncertainty=True,
    energy_uncertainty_pct=10.0,       # Standard monitoring
    carbon_intensity_uncertainty_pct=15.0,  # Regional grid estimates
    pue_uncertainty_pct=5.0,           # Industry average PUE
)
```
**Expected Result**: ±10-20% relative uncertainty (moderate precision)

### Edge/Mobile Environments
**Use Case**: IoT devices, mobile computing, estimated measurements

```python
tracker = UncertaintyAwareEmissionsTracker(
    enable_uncertainty=True,
    energy_uncertainty_pct=25.0,       # Estimated power consumption
    carbon_intensity_uncertainty_pct=30.0,  # Uncertain grid mix
    pue_uncertainty_pct=15.0,          # Unknown infrastructure efficiency
)
```
**Expected Result**: ±25-40% relative uncertainty (low precision)

## Understanding the Results

### Confidence Intervals
```python
emissions_data = tracker.stop()
print(f"Point estimate: {emissions_data.emissions:.4f} kg CO₂")
print(f"95% CI: [{emissions_data.emissions_ci_lower_kg:.4f}, {emissions_data.emissions_ci_upper_kg:.4f}]")
print(f"Relative uncertainty: ±{emissions_data.relative_uncertainty_pct:.1f}%")
```

### Quality Assessment
The system automatically classifies precision quality:

| Relative Uncertainty | Quality Classification | Use Cases |
|---------------------|----------------------|-----------|
| ≤5% | `high_precision` | Scientific computing, compliance reporting |
| 5-15% | `moderate_precision` | Production systems, carbon budgeting |
| 15-25% | `low_precision` | Exploratory analysis, rough estimates |
| >25% | `very_low_precision` | Order-of-magnitude estimates |

### Interpreting Confidence Intervals

**95% Confidence Interval [0.0039, 0.0052] kg CO₂** means:
- We are 95% confident the true emissions are between 0.0039 and 0.0052 kg CO₂
- There's a 5% chance the true value is outside this range
- The measurement precision supports decisions requiring ±30% accuracy

## Integration with Existing Workflows

### CSV Output Enhancement
When uncertainty is enabled, additional columns are automatically added:

```csv
timestamp,project_name,emissions,emissions_ci_lower_kg,emissions_ci_upper_kg,relative_uncertainty_pct,uncertainty_quality,...
```

### API Integration
The uncertainty metadata integrates with CodeCarbon APIs:

```python
# Uncertainty data is included in API submissions
uncertainty_dict = emissions_data.to_uncertainty_dict()
print(uncertainty_dict)
```

Output:
```python
{
    "uncertainty_enabled": True,
    "method": "monte_carlo", 
    "emissions_kg": 0.0045,
    "ci_lower_kg": 0.0039,
    "ci_upper_kg": 0.0052,
    "confidence_level_pct": 95.0,
    "relative_uncertainty_pct": 14.4,
    "quality_assessment": "moderate_precision"
}
```

## Performance Considerations

### Computational Overhead
- **Monte Carlo Analysis**: ~1-5ms overhead per emissions calculation
- **Memory Usage**: ~50KB additional memory for sample storage
- **Recommendation**: Negligible impact for typical tracking intervals (≥1 second)

### Optimization Tips
```python
# For high-frequency tracking, reduce samples
tracker = UncertaintyAwareEmissionsTracker(
    monte_carlo_samples=200,  # Faster but less smooth distributions
)

# For rare but critical measurements, increase samples  
tracker = UncertaintyAwareEmissionsTracker(
    monte_carlo_samples=10000,  # Slower but more precise confidence intervals
)
```

## Disabling Uncertainty Analysis

For backward compatibility or performance-critical applications:

```python
tracker = UncertaintyAwareEmissionsTracker(
    enable_uncertainty=False  # Behaves like standard EmissionsTracker
)
```

## Validation and Testing

Run the included demonstration script:

```bash
python examples/uncertainty_demo.py
```

This script demonstrates:
- Basic uncertainty tracking
- Precision level comparisons
- Confidence interval variations
- Performance benchmarking

## Literature References

The uncertainty parameters are based on published research:

1. **Energy Measurement Uncertainty**: 
   - Smart meters: ±2-5% (IEC 62053-21)
   - Estimated consumption: ±15-30% (Henderson et al., 2014)

2. **Carbon Intensity Uncertainty**:
   - Grid mix temporal variation: ±10-25% (Hawkes, 2010) 
   - Regional estimation error: ±20-40% (Tranberg et al., 2019)

3. **PUE Uncertainty**:
   - Measured datacenters: ±3-8% (Koomey et al., 2011)
   - Industry estimates: ±10-20% (Masanet et al., 2020)

## Migration from Standard Tracker

Simple replacement:

```python
# Before
from codecarbon import EmissionsTracker
tracker = EmissionsTracker(project_name="my_project")

# After 
from codecarbon.uncertainty_emissions_tracker import UncertaintyAwareEmissionsTracker
tracker = UncertaintyAwareEmissionsTracker(
    project_name="my_project",
    enable_uncertainty=True
)
```

All existing parameters and behaviors are preserved.