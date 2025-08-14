"""
Download CHIRPS climate data from UCSB archive.

This module provides functionality to download CHIRPS (Climate Hazards Group
InfraRed Precipitation with Station data) rainfall datasets from the UCSB
Climate Hazards Group archive.
"""

import gzip
import re
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm


def chirps_options() -> pd.DataFrame:
    """
    List Available Monthly CHIRPS Dataset Options.

    Returns a DataFrame with supported **monthly** CHIRPS datasets available
    for
    download using the `download_chirps()` function. Each entry includes the
    dataset code, descriptive label, and the subdirectory path on the CHIRPS
    FTP server where `.tif.gz` files are stored.

    Returns:
        pd.DataFrame: DataFrame with columns:
            - dataset: Machine-readable dataset code (e.g., "africa_monthly")
            - frequency: Data frequency (currently only "monthly")
            - label: Descriptive label for user display
            - subdir: Subdirectory path to the CHIRPS TIFF archive

    Example:
        >>> options = chirps_options()
        >>> print(options)
    """
    return pd.DataFrame(
        {
            "dataset": [
                "global_monthly",
                "africa_monthly",
                "camer-carib_monthly",
                "EAC_monthly",
            ],
            "frequency": ["monthly"] * 4,
            "label": [
                "Global (Monthly)",
                "Africa (Monthly)",
                "Caribbean & Central America (Monthly)",
                "East African Community (Monthly)",
            ],
            "subdir": [
                "global_monthly/tifs",
                "africa_monthly/tifs",
                "camer-carib_monthly/tifs",
                "EAC_monthly/tifs",
            ],
        }
    )


def check_chirps_available(
    dataset_code: str = "africa_monthly",
) -> Optional[pd.DataFrame]:
    """
    List Available CHIRPS Raster Files for a Dataset.

    Scrapes the UCSB CHIRPS archive to list available `.tif.gz` raster files
    for a given dataset (e.g., "africa_monthly"). Extracts year and month
    from filenames where possible.

    Args:
        dataset_code: One of the dataset codes from chirps_options(),
                     such as "africa_monthly".

    Returns:
        pd.DataFrame or None: DataFrame with columns:
            - file_name: The filename of the `.tif.gz` raster
            - year: Extracted year (YYYY) from filename
            - month: Extracted month (MM) from filename, if available
            - dataset: The dataset code queried
        Returns None if the dataset cannot be accessed.

    Example:
        >>> files = check_chirps_available("africa_monthly")
        >>> if files is not None:
        ...     print(f"Available files: {len(files)}")
    """
    base_url = (
        f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/{dataset_code}/tifs/"
    )

    try:
        response = requests.get(base_url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, "html.parser")
        links = soup.find_all("a")
        files = [link.get_text() for link in links]
        files = [f for f in files if f.endswith(".tif.gz")]

        if not files:
            print(f"No valid CHIRPS files found for {dataset_code}.")
            return None

        data = []
        for file_name in files:
            # Extract year (4 digits)
            year_match = re.search(r"\d{4}", file_name)
            year = year_match.group() if year_match else None

            # Extract month (2 digits after year and dot)
            month_match = re.search(r"\d{4}\.(\d{2})", file_name)
            month = month_match.group(1) if month_match else None

            if year:  # Only include files with valid year
                data.append(
                    {
                        "file_name": file_name,
                        "year": year,
                        "month": month,
                        "dataset": dataset_code,
                    }
                )

        if not data:
            print(f"No valid CHIRPS files found for {dataset_code}.")
            return None

        df = pd.DataFrame(data)
        df = df.sort_values(["year", "month"], ascending=[False, True])

        # Calculate date range for info message
        try:
            dates = pd.to_datetime(
                df["year"] + "-" + df["month"] + "-01", errors="coerce"
            ).dropna()
            if len(dates) > 0:
                start_date = dates.min().strftime("%b %Y")
                end_date = dates.max().strftime("%b %Y")
                print(
                    f"✓ {dataset_code}: Data available from {start_date} to "
                    f"{end_date}."
                )
        except Exception:
            years = df["year"].dropna()
            if len(years) > 0:
                print(
                    f"✓ {dataset_code}: Data available {years.min()} - "
                    f"{years.max()}."
                )

        return df

    except Exception as e:
        print(f"✗ Could not access {base_url}: {e}")
        return None


def download_chirps(
    dataset: str,
    start: str,
    end: Optional[str] = None,
    out_dir: str = ".",
    unzip: bool = True,
) -> None:
    """
    Download CHIRPS Raster Data from UCSB Archive.

    Downloads `.tif.gz` CHIRPS rainfall data files from the UCSB Climate
    Hazards
    Group archive for a specified dataset and date range. Files are downloaded
    and optionally unzipped to a local directory.

    Use chirps_options() to view all available datasets and their metadata.

    Args:
        dataset: One of the dataset codes listed in chirps_options()
        start: Start date in "YYYY-MM" format (e.g., "2020-01")
        end: End date in "YYYY-MM" format. If None, only start month is
            downloaded
        out_dir: Directory path where downloaded files will be saved.
                Will be created if it does not exist
        unzip: If True, the `.tif.gz` files will be unzipped after download

    Example:
        >>> # View available datasets
        >>> print(chirps_options())
        >>>
        >>> # Download Africa monthly CHIRPS for Jan-Mar 2022
        >>> download_chirps(
        ...     dataset="africa_monthly",
        ...     start="2022-01",
        ...     end="2022-03",
        ...     out_dir="chirps_data"
        ... )
    """
    # Validate dataset
    opts = chirps_options()
    if dataset not in opts["dataset"].values:
        raise ValueError(
            "Invalid dataset. Use chirps_options() to see available options."
        )

    # Get dataset info
    sel = opts[opts["dataset"] == dataset].iloc[0]
    freq = sel["frequency"]
    subdir = sel["subdir"]
    base_url = f"https://data.chc.ucsb.edu/products/CHIRPS-2.0/{subdir}/"

    # Generate date range
    try:
        start_date = pd.to_datetime(f"{start}-01")
        if end is None:
            dates = [start_date]
        else:
            end_date = pd.to_datetime(f"{end}-01")
            dates = list(pd.date_range(start_date, end_date, freq="MS"))
    except Exception as e:
        raise ValueError(f"Invalid date format. Use YYYY-MM format: {e}")

    # Create output directory
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Downloading CHIRPS: {sel['label']} ===")

    # Download files with progress bar
    for date in tqdm(dates, desc="Downloading"):
        year = date.strftime("%Y")
        month = date.strftime("%m")

        if freq == "monthly":
            orig_name = f"chirps-v2.0.{year}.{month}.tif.gz"
            custom_name = f"{dataset}_chirps-v2.0.{year}.{month}.tif.gz"
            url = urljoin(base_url, orig_name)
            dest = out_path / custom_name
            tif_file = out_path / f"{dataset}_chirps-v2.0.{year}.{month}.tif"

            # Skip if unzipped file already exists
            if tif_file.exists():
                tqdm.write(f"ℹ  Skipping {tif_file.name}, already exists.")
                continue

            try:
                response = requests.get(url, timeout=60, stream=True)
                response.raise_for_status()

                # Download with progress
                with open(dest, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)

                tqdm.write(f"✓ Downloaded {custom_name}")

                # Unzip if requested
                if unzip and dest.exists():
                    with gzip.open(dest, "rb") as f_in:
                        with open(tif_file, "wb") as f_out:
                            f_out.write(f_in.read())

                    # Remove the .gz file after unzipping
                    dest.unlink()
                    tqdm.write(f"✓ Unzipped to {tif_file.name}")

            except Exception as e:
                tqdm.write(f"✗ Failed {custom_name}: {e}")

    print("\n✓ All CHIRPS files processed")
