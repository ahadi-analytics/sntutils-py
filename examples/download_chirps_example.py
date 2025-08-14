#!/usr/bin/env python3
"""
Example script demonstrating how to use sntutils-py CHIRPS download functionality.

This script shows how to:
1. View available CHIRPS datasets
2. Check what files are available for a dataset
3. Download CHIRPS data for a specific time period
"""

from pathlib import Path
from sntutils.climate.download_chirps import (
    chirps_options,
    check_chirps_available,
    download_chirps,
)


def main():
    """Run the CHIRPS download example."""
    print("=== CHIRPS Download Example ===\n")
    
    # 1. Show available datasets
    print("1. Available CHIRPS datasets:")
    options = chirps_options()
    print(options.to_string(index=False))
    print()
    
    # 2. Check what's available for Africa monthly dataset
    print("2. Checking available files for Africa monthly dataset:")
    available = check_chirps_available("africa_monthly")
    
    if available is not None:
        print(f"   Found {len(available)} files")
        print("   Latest 5 files:")
        print(available.head().to_string(index=False))
    else:
        print("   Could not retrieve file list (check internet connection)")
    print()
    
    # 3. Download a small sample (just one month)
    print("3. Downloading sample data (Jan 2023) to ./data/chirps/:")
    
    # Create output directory
    output_dir = Path("./data/chirps")
    
    try:
        download_chirps(
            dataset="africa_monthly",
            start="2023-01",
            end=None,  # Just one month
            out_dir=str(output_dir),
            unzip=True
        )
        
        # Show what was downloaded
        downloaded_files = list(output_dir.glob("*.tif"))
        if downloaded_files:
            print(f"\n✓ Successfully downloaded {len(downloaded_files)} file(s):")
            for file in downloaded_files:
                file_size = file.stat().st_size / (1024 * 1024)  # MB
                print(f"   - {file.name} ({file_size:.1f} MB)")
        else:
            print("\n⚠  No files were downloaded (may already exist)")
            
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        print("   This might be due to:")
        print("   - No internet connection")
        print("   - CHIRPS server is down")
        print("   - The requested file doesn't exist")
    
    print("\n=== Example Complete ===")


if __name__ == "__main__":
    main()