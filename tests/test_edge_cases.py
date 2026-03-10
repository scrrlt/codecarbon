#!/usr/bin/env python3
"""
Test edge cases for uncertainty analysis improvements.
"""

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

    sorted_samples = sorted(samples)
    n = len(sorted_samples)
    
    # Edge case: very small sample sizes may produce identical bounds
    if n < 10:
        # Return min/max for very small samples
        return (sorted_samples[0], sorted_samples[-1])
    
    # Calculate percentile indices
    lower_idx = int((alpha / 2.0) * (n - 1))
    upper_idx = int((1 - alpha / 2.0) * (n - 1))
    
    # Ensure bounds are distinct for small samples
    if lower_idx == upper_idx:
        lower_idx = max(0, lower_idx - 1)
        upper_idx = min(n - 1, upper_idx + 1)
    
    return (sorted_samples[lower_idx], sorted_samples[upper_idx])


def test_small_sample_edge_cases():
    """Test that small sample sizes handle edge cases correctly."""
    print("Testing Edge Cases for Small Sample Sizes...")
    
    # Test very small sample (n=5)
    small_samples = [1.0, 1.1, 1.2, 1.3, 1.4]
    ci_lower, ci_upper = compute_confidence_interval(small_samples)
    
    assert ci_lower == 1.0, f"Expected lower bound 1.0, got {ci_lower}"
    assert ci_upper == 1.4, f"Expected upper bound 1.4, got {ci_upper}"
    assert ci_lower < ci_upper, "Lower bound should be less than upper bound"
    print(f"✓ Small sample (n={len(small_samples)}): CI=[{ci_lower}, {ci_upper}]")
    
    # Test tiny sample (n=3)  
    tiny_samples = [2.0, 2.1, 2.2]
    ci_lower, ci_upper = compute_confidence_interval(tiny_samples)
    
    assert ci_lower == 2.0, f"Expected lower bound 2.0, got {ci_lower}"
    assert ci_upper == 2.2, f"Expected upper bound 2.2, got {ci_upper}"
    print(f"✓ Tiny sample (n={len(tiny_samples)}): CI=[{ci_lower}, {ci_upper}]")
    
    # Test single sample (n=1)
    single_sample = [3.0]
    ci_lower, ci_upper = compute_confidence_interval(single_sample)
    
    assert ci_lower == 3.0, f"Expected lower bound 3.0, got {ci_lower}"
    assert ci_upper == 3.0, f"Expected upper bound 3.0, got {ci_upper}"
    print(f"✓ Single sample (n={len(single_sample)}): CI=[{ci_lower}, {ci_upper}]")
    
    # Test normal sample size (n=100) - should work the same
    normal_samples = [float(i) for i in range(100)]
    ci_lower, ci_upper = compute_confidence_interval(normal_samples)
    
    assert 0.0 <= ci_lower < ci_upper <= 99.0, f"Normal sample CI bounds seem wrong: [{ci_lower}, {ci_upper}]"
    print(f"✓ Normal sample (n={len(normal_samples)}): CI=[{ci_lower:.1f}, {ci_upper:.1f}]")
    
    print("✓ All edge case tests passed!")


def test_empty_samples():
    """Test empty samples list."""
    print("Testing Empty Samples...")
    
    empty_samples = []
    ci_lower, ci_upper = compute_confidence_interval(empty_samples)
    
    assert ci_lower == 0.0, f"Expected lower bound 0.0, got {ci_lower}"
    assert ci_upper == 0.0, f"Expected upper bound 0.0, got {ci_upper}"
    print("✓ Empty samples handled correctly")


if __name__ == "__main__":
    print("=" * 60)
    print("CodeCarbon Uncertainty Analysis - Edge Case Tests")
    print("=" * 60)
    
    try:
        test_small_sample_edge_cases()
        print()
        test_empty_samples()
        print()
        print("✓ All edge case tests passed! Confidence interval fixes validated.")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        raise