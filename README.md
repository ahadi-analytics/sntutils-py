# sntutils-py

[![Python package](https://github.com/ahadi-analytics/sntutils-py/actions/workflows/python-package.yml/badge.svg)](https://github.com/ahadi-analytics/sntutils-py/actions/workflows/python-package.yml)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/ahadi-analytics/sntutils-py/actions)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)

Python utility functions for data acquisition, preparation and analysis in Subnational Tailoring of Malaria Interventions (SNT).

## Installation

### From PyPI

```bash
pip install sntutils-py
```

### From GitHub

```bash
# Using pip
pip install git+https://github.com/ahadi-analytics/sntutils-py.git

# Using uv (recommended)
uv add git+https://github.com/ahadi-analytics/sntutils-py.git

# Development install (editable)
pip install -e git+https://github.com/ahadi-analytics/sntutils-py.git#egg=sntutils-py
# or with uv
uv add --editable git+https://github.com/ahadi-analytics/sntutils-py.git

# Specific branch/tag
pip install git+https://github.com/ahadi-analytics/sntutils-py.git@main
# or with uv
uv add git+https://github.com/ahadi-analytics/sntutils-py.git@main
```

### From R (using reticulate)

For R users who want to use this Python package in their R environment:

```r
# Install reticulate if you haven't already
install.packages("reticulate")

# Install sntutils from GitHub
reticulate::py_install("git+https://github.com/ahadi-analytics/sntutils-py.git")

# Use the package in R
sntutils <- reticulate::import("sntutils")
```

### In requirements.txt

```
git+https://github.com/ahadi-analytics/sntutils-py.git
```

### In pyproject.toml

```toml
dependencies = [
    "sntutils-py @ git+https://github.com/ahadi-analytics/sntutils-py.git"
]
```

### From Source

```bash
# Install from source
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

```python
from sntutils.climate import download_chirps, chirps_options, check_chirps_available
from sntutils.geo import prep_geonames
```

## Download Climate Data (CHIRPS Rainfall)

The `download_chirps()` function allows you to fetch CHIRPS monthly rainfall raster data for any supported region and time period. It pulls data directly from the UCSB Climate Hazards Group FTP archive and supports automatic unzipping. Only .tif.gz monthly rasters are supported, and the function avoids re-downloading existing files. To view all supported CHIRPS datasets, use `chirps_options()`. To check the available years and months for a specific CHIRPS dataset (e.g., africa_monthly), use the `check_chirps_available()` function.

```python
# View available CHIRPS datasets
options = chirps_options()
print(options)
#                  dataset frequency                                   label                      subdir
# 0         global_monthly   monthly                        Global (Monthly)         global_monthly/tifs
# 1         africa_monthly   monthly                        Africa (Monthly)         africa_monthly/tifs
# 2    camer-carib_monthly   monthly   Caribbean & Central America (Monthly)    camer-carib_monthly/tifs
# 3            EAC_monthly   monthly        East African Community (Monthly)            EAC_monthly/tifs
```

```python
# Check available years and months for the africa_monthly dataset
available_files = check_chirps_available(dataset_code="africa_monthly")

# ✓ africa_monthly: Data available from Jan 1981 to Mar 2025.
print(available_files.head(10))
#                  file_name  year month        dataset
# 0  chirps-v2.0.2025.01.tif.gz  2025    01  africa_monthly
# 1  chirps-v2.0.2025.02.tif.gz  2025    02  africa_monthly
# 2  chirps-v2.0.2025.03.tif.gz  2025    03  africa_monthly
# 3  chirps-v2.0.2024.01.tif.gz  2024    01  africa_monthly
# 4  chirps-v2.0.2024.02.tif.gz  2024    02  africa_monthly
# 5  chirps-v2.0.2024.03.tif.gz  2024    03  africa_monthly
# 6  chirps-v2.0.2024.04.tif.gz  2024    04  africa_monthly
# 7  chirps-v2.0.2024.05.tif.gz  2024    05  africa_monthly
# 8  chirps-v2.0.2024.06.tif.gz  2024    06  africa_monthly
# 9  chirps-v2.0.2024.07.tif.gz  2024    07  africa_monthly
```

```python
# Download Africa monthly rainfall for Jan to Mar 2022
download_chirps(
    dataset="africa_monthly",
    start="2022-01",
    end="2022-03",
    out_dir="data/chirps"
)

# === Downloading CHIRPS: Africa (Monthly) ===
# Downloading: 100%|██████████| 3/3 [00:45<00:00, 15.23s/it]
# ✓ Downloaded africa_monthly_chirps-v2.0.2022.01.tif.gz
# ✓ Unzipped to africa_monthly_chirps-v2.0.2022.01.tif
# ✓ Downloaded africa_monthly_chirps-v2.0.2022.02.tif.gz
# ✓ Unzipped to africa_monthly_chirps-v2.0.2022.02.tif
# ✓ Downloaded africa_monthly_chirps-v2.0.2022.03.tif.gz
# ✓ Unzipped to africa_monthly_chirps-v2.0.2022.03.tif
# ✓ All CHIRPS files processed
```

This will download the following files to the `data/chirps/` folder (and unzip them if requested):

- `africa_monthly_chirps-v2.0.2022.01.tif`
- `africa_monthly_chirps-v2.0.2022.02.tif`
- `africa_monthly_chirps-v2.0.2022.03.tif`

## Harmonize Administrative Names

The `prep_geonames()` function harmonizes administrative names in datasets to match standard geonames, supporting hierarchical matching from country down to district levels. It uses string distance algorithms and interactive menus for manual corrections when needed.

```python
from sntutils.geo import prep_geonames
import pandas as pd

# Load your data with administrative names
data = pd.DataFrame({
    'country': ['Kenya', 'Uganda', 'Tanzania'],
    'region': ['Nairobi', 'Kampala', 'Dar es Salaam'],
    'district': ['Westlands', 'Central', 'Kinondoni']
})

# Harmonize names against standard geonames
# Load lookup data
lookup_df = pd.read_csv("geonames.csv")

harmonized_data = prep_geonames(
    target_df=data,            # Your data to harmonize
    lookup_df=lookup_df,       # Reference geonames dataframe
    level0='country',          # Country column in both dataframes
    level1='region',           # Region column in both dataframes
    level2='district',         # District column in both dataframes
    method="jw",               # Jaro-Winkler distance (or "lv" for Levenshtein)
    cache_path="cache.xlsx",   # Cache manual corrections (format auto-detected from extension)
    preserve_case=True         # Preserve original case in output
)

# The function returns the harmonized dataframe directly
print(harmonized_data[['country', 'region', 'district']])
```

### Features

- **Hierarchical matching**: Matches names at multiple administrative levels (country → province → district)
- **String distance algorithms**: Supports Jaro-Winkler (`method="jw"`) and Levenshtein (`method="lv"`) distance metrics
- **Interactive correction**: Presents menu options for manual name corrections when fuzzy matching fails
- **Caching**: Saves manual corrections to avoid repeat work across sessions
- **Batch processing**: Efficiently processes large datasets with progress tracking
- **Match statistics**: Displays detailed statistics about successful matches at each level
- **Case preservation**: Option to maintain original case in output while matching case-insensitively

### Cache Management

The function maintains a cache of manual corrections to streamline repeat harmonization:

```python
# Load and inspect cache
from sntutils.geo import load_cache, save_cache

cache = load_cache("cache.xlsx", format="excel")
print(cache.head())

# Cache columns include:
# - level: Administrative level (level0, level1, etc.)
# - name_to_match: Original name from your data
# - replacement: Corrected/harmonized name
# - level0_prepped through level4_prepped: Hierarchical structure
# - created_time: When the correction was made
# - name_of_creator: User who made the correction
```

## Examples

See the `examples/` directory for complete usage examples:

```bash
python examples/download_chirps_example.py
```

## Development

```bash
# Install development dependencies
uv add --dev pytest pytest-cov black flake8 mypy pre-commit

# Install the package in editable mode
uv pip install -e .

# Run tests
uv run pytest

# Format code
uv run black src tests

# Lint code
uv run flake8 src tests

# Type checking
uv run mypy src
```

## Project Structure

```
sntutils-py/
├── src/sntutils/              # Main package
│   ├── climate/               # Climate data utilities
│   ├── geo/                   # Geographic harmonization utilities
│   └── utils/                 # General utilities
├── tests/                     # Test suite
├── examples/                  # Usage examples
└── docs/                      # Documentation
```
