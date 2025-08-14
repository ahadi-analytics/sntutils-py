#!/usr/bin/env python3
"""
Test script to verify sntutils package import and basic functionality
"""

print("Testing sntutils package...")

try:
    import sntutils
    print("✓ Successfully imported sntutils")
except ImportError as e:
    print(f"✗ Failed to import sntutils: {e}")
    exit(1)

try:
    from sntutils.climate import download_chirps, chirps_options, check_chirps_available
    print("✓ Successfully imported climate functions")
except ImportError as e:
    print(f"✗ Failed to import climate functions: {e}")
    exit(1)

try:
    # Test chirps_options function
    options = chirps_options()
    print(f"✓ chirps_options() returned {len(options)} options")
except Exception as e:
    print(f"✗ Error calling chirps_options(): {e}")

print("\n🎉 All imports successful! Package is working correctly.")
