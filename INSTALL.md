# Installation Guide for sntutils

## Basic Installation

The basic installation includes all core dependencies needed for the main functionality:

```bash
pip install sntutils
```

This installs:
- **Data processing**: pandas, numpy
- **Web scraping**: requests, beautifulsoup4, lxml
- **Progress bars**: tqdm
- **String matching**: python-Levenshtein
- **CLI interface**: rich (for better terminal output)
- **Configuration**: pyyaml (for config files)

## Full Installation (All Features)

To install with ALL optional dependencies for complete functionality:

```bash
pip install sntutils[all]
```

This adds:
- **Geospatial support**: geopandas
- **Excel files**: openpyxl
- **Parquet/Feather formats**: pyarrow
- **Advanced string matching**: stringdist
- **R file support**: pyreadr
- **CLI commands**: click

## Feature-Specific Installations

### For Geospatial Analysis
```bash
pip install sntutils[geo]
```
Includes: geopandas, shapely, fiona

### For Excel Support
```bash
pip install sntutils[excel]
```
Includes: openpyxl, xlsxwriter

### For Additional File Formats
```bash
pip install sntutils[formats]
```
Includes: pyarrow (Parquet/Feather), fastparquet, pyreadr (R RDS files)

### For Development
```bash
pip install sntutils[dev]
```
Includes: pytest, black, flake8, mypy, pre-commit, type stubs

### For Documentation
```bash
pip install sntutils[docs]
```
Includes: sphinx, sphinx-rtd-theme, myst-parser

## Multiple Feature Groups

You can combine multiple optional dependency groups:

```bash
# Install with geo and excel support
pip install sntutils[geo,excel]

# Install with all features plus dev tools
pip install sntutils[all,dev]
```

## Installation from Source

### Using pip
```bash
git clone https://github.com/ahadi-analytics/sntutils-py.git
cd sntutils-py
pip install -e .

# Or with all optional dependencies
pip install -e ".[all]"

# Or for development
pip install -e ".[dev]"
```

### Using uv (Recommended for Development)
```bash
git clone https://github.com/ahadi-analytics/sntutils-py.git
cd sntutils-py
uv sync --dev  # Installs all dev dependencies
uv pip install -e .  # Editable install
```

## Verifying Installation

After installation, verify everything works:

```python
# Test basic import
import sntutils
print(sntutils.__version__)

# Test CHIRPS functionality
from sntutils.climate import chirps_options
print(chirps_options())

# Test harmonization functionality
from sntutils.geo import prep_geonames
# prep_geonames is now available
```

## Troubleshooting

### Missing Optional Dependencies

If you encounter messages like:
- "Warning: openpyxl not installed" - Install with `pip install sntutils[excel]`
- "Warning: pyarrow not installed" - Install with `pip install sntutils[formats]`
- GeoPandas errors - Install with `pip install sntutils[geo]`

### Platform-Specific Issues

#### Windows
Some dependencies like geopandas may require additional steps on Windows:
```bash
# Install using conda first (recommended)
conda install geopandas
pip install sntutils

# Or use precompiled wheels
pip install pipwin
pipwin install gdal fiona
pip install sntutils[geo]
```

#### macOS
If you encounter issues with GDAL:
```bash
brew install gdal
pip install sntutils[geo]
```

#### Linux
Install system dependencies first:
```bash
# Ubuntu/Debian
sudo apt-get install gdal-bin libgdal-dev

# Fedora
sudo dnf install gdal gdal-devel

pip install sntutils[all]
```

## Minimal Installation (No Optional Features)

If you want the absolute minimum installation without even Rich or PyYAML:

```bash
pip install --no-deps sntutils
pip install requests pandas numpy beautifulsoup4 lxml tqdm python-Levenshtein
```

## Checking Installed Features

To check which optional features are available:

```python
from sntutils.geo.harmonize_admin_names import RICH_AVAILABLE
print(f"Rich CLI: {RICH_AVAILABLE}")

# Check for Excel support
try:
    import openpyxl
    print("Excel support: Available")
except ImportError:
    print("Excel support: Not installed")

# Check for geospatial support
try:
    import geopandas
    print("GeoPandas: Available")
except ImportError:
    print("GeoPandas: Not installed")
```

## Updating

To update to the latest version:

```bash
pip install --upgrade sntutils

# Or with all features
pip install --upgrade sntutils[all]
```