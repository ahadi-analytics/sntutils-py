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
│   └── utils/                 # General utilities
├── tests/                     # Test suite
├── examples/                  # Usage examples
└── docs/                      # Documentation
```
