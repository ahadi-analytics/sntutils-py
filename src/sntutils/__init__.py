"""
sntutils-py: Utility Functions for Data Preparation and Analysis in
Subnational Tailoring of Malaria Interventions (SNT)

A Python package for health data analysis, particularly for malaria
interventions at subnational levels.
"""

__version__ = "0.1.0"
__author__ = "Mohamed A. Yusuf"
__email__ = "mohamedayusuf87@gmail.com"

from .climate.download_chirps import (
    chirps_options,
    check_chirps_available,
    download_chirps,
)

__all__ = [
    "chirps_options",
    "check_chirps_available",
    "download_chirps",
]
