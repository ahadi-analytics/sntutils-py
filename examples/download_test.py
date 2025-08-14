#!/usr/bin/env python3
"""
Download CHIRPS data test script
"""

from sntutils.climate import download_chirps

print("Starting CHIRPS data download...")

download_chirps(
    dataset="africa_monthly",
    start="2022-01",
    end="2022-03",
    out_dir="data/chirps"
)

print("Download completed!")