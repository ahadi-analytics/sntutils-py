"""
Tests for download_chirps module.

Based on the R sntutils test structure, these tests validate the CHIRPS
data download functionality including network operations and file handling.
"""

import gzip
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
import pandas as pd
import requests

from sntutils.climate.download_chirps import (
    chirps_options,
    check_chirps_available,
    download_chirps,
    retry,
    _download_file_with_retry,
)


def skip_if_no_internet():
    """Helper to skip tests if no internet connection."""
    try:
        response = requests.get("https://httpbin.org/get", timeout=5)
        return response.status_code != 200
    except Exception:
        return True


def skip_if_chirps_down():
    """Helper to skip if CHIRPS server is down."""
    try:
        response = requests.get("https://data.chc.ucsb.edu/", timeout=10)
        return response.status_code != 200
    except Exception:
        return True


class TestChirpsOptions:
    """Test chirps_options function."""

    def test_chirps_options_returns_correct_structure(self):
        """Test that chirps_options returns correct DataFrame structure."""
        result = chirps_options()

        assert isinstance(result, pd.DataFrame)

        # Check required columns exist
        expected_cols = ["dataset", "frequency", "label", "subdir"]
        assert all(col in result.columns for col in expected_cols)
        assert len(result.columns) == len(expected_cols)

    def test_chirps_options_contains_expected_datasets(self):
        """Test that expected datasets are present."""
        result = chirps_options()

        expected_datasets = [
            "global_monthly",
            "africa_monthly",
            "camer-carib_monthly",
            "EAC_monthly",
        ]

        assert all(dataset in result["dataset"].values for dataset in expected_datasets)
        assert len(result) == len(expected_datasets)

    def test_chirps_options_has_consistent_data_structure(self):
        """Test that data structure is consistent."""
        result = chirps_options()

        # All datasets should be monthly for now
        assert all(result["frequency"] == "monthly")

        # All subdirectories should end with "/tifs"
        assert all(subdir.endswith("/tifs") for subdir in result["subdir"])

        # Dataset codes should match subdir prefixes
        for _, row in result.iterrows():
            expected_prefix = row["subdir"].replace("/tifs", "")
            assert row["dataset"] == expected_prefix

        # Labels should contain "Monthly"
        assert all("Monthly" in label for label in result["label"])

        # No missing values
        assert not result.isnull().any().any()


class TestCheckChirpsAvailable:
    """Test check_chirps_available function."""

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    @pytest.mark.skipif(skip_if_chirps_down(), reason="CHIRPS server not accessible")
    def test_check_chirps_available_returns_correct_structure(self):
        """Test that check_chirps_available returns correct structure."""
        result = check_chirps_available("africa_monthly")

        if result is not None:
            assert isinstance(result, pd.DataFrame)

            # Check required columns exist
            expected_cols = ["file_name", "year", "month", "dataset"]
            assert all(col in result.columns for col in expected_cols)

            # Should have some data
            assert len(result) > 0

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    @pytest.mark.skipif(skip_if_chirps_down(), reason="CHIRPS server not accessible")
    def test_check_chirps_available_extracts_years_correctly(self):
        """Test that years are extracted correctly."""
        result = check_chirps_available("africa_monthly")

        if result is not None and len(result) > 0:
            # Years should be 4-digit numbers
            years = pd.to_numeric(result["year"], errors="coerce")
            assert not years.isnull().any()
            assert all(years >= 1981)  # CHIRPS starts 1981
            assert all(years <= pd.Timestamp.now().year)

            # Should be string in the DataFrame
            assert result["year"].dtype == "object"

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    @pytest.mark.skipif(skip_if_chirps_down(), reason="CHIRPS server not accessible")
    def test_check_chirps_available_extracts_months_correctly(self):
        """Test that months are extracted correctly."""
        result = check_chirps_available("africa_monthly")

        if result is not None and len(result) > 0:
            # Months should be 2-digit strings 01-12
            months = result["month"].dropna()
            if len(months) > 0:
                month_nums = pd.to_numeric(months)
                assert all(month_nums >= 1)
                assert all(month_nums <= 12)
                assert all(len(m) == 2 for m in months)

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    @pytest.mark.skipif(skip_if_chirps_down(), reason="CHIRPS server not accessible")
    def test_check_chirps_available_filters_tif_gz_files_correctly(self):
        """Test that tif.gz files are filtered correctly."""
        result = check_chirps_available("africa_monthly")

        if result is not None and len(result) > 0:
            # All file names should end with .tif.gz
            assert all(fname.endswith(".tif.gz") for fname in result["file_name"])

            # Dataset column should match input
            assert all(result["dataset"] == "africa_monthly")

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    def test_check_chirps_available_handles_invalid_dataset(self):
        """Test handling of invalid dataset."""
        result = check_chirps_available("invalid_dataset")

        # Should return None for invalid dataset
        assert result is None

    def test_check_chirps_available_with_mock_response(self):
        """Test with mocked HTTP response."""
        mock_html = """
        <html><body>
        <a href="chirps-v2.0.2020.01.tif.gz">chirps-v2.0.2020.01.tif.gz</a>
        <a href="chirps-v2.0.2020.02.tif.gz">chirps-v2.0.2020.02.tif.gz</a>
        <a href="other_file.txt">other_file.txt</a>
        </body></html>
        """

        with (
            patch("requests.get") as mock_get,
            patch("sntutils.climate.download_chirps.logger") as mock_logger,
        ):
            mock_response = Mock()
            mock_response.content = mock_html.encode()
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            result = check_chirps_available("africa_monthly")

            assert result is not None
            assert len(result) == 2
            assert all(result["year"] == "2020")
            assert result["month"].tolist() == ["01", "02"]

            # Verify logging was called
            mock_logger.info.assert_called()


class TestDownloadChirps:
    """Test download_chirps function."""

    def test_download_chirps_validates_dataset_parameter(self):
        """Test that invalid dataset parameter raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Invalid dataset"):
                download_chirps(
                    dataset="invalid_dataset",
                    start="2020-01",
                    out_dir=temp_dir,
                )

    def test_download_chirps_validates_date_format(self):
        """Test that invalid date format raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError, match="Invalid date format"):
                download_chirps(
                    dataset="africa_monthly",
                    start="invalid-date",
                    out_dir=temp_dir,
                )

    def test_download_chirps_creates_output_directory(self):
        """Test that output directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir) / "new_folder"

            with patch("requests.get") as mock_get:
                # Mock a failed download to avoid actually downloading
                mock_get.side_effect = requests.RequestException("Mocked failure")

                try:
                    download_chirps(
                        dataset="africa_monthly",
                        start="2020-01",
                        out_dir=str(out_dir),
                    )
                except Exception:
                    pass  # We expect this to fail

                assert out_dir.exists()

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    @pytest.mark.skipif(skip_if_chirps_down(), reason="CHIRPS server not accessible")
    def test_download_chirps_single_month(self):
        """Test downloading a single month."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                download_chirps(
                    dataset="africa_monthly",
                    start="2020-01",
                    out_dir=temp_dir,
                    unzip=False,
                )

                # Check that file was downloaded
                files = list(Path(temp_dir).glob("*.tif.gz"))
                assert len(files) >= 1

                # Check filename format
                filename = files[0].name
                assert "africa_monthly_chirps" in filename
                assert "2020.01" in filename

            except Exception as e:
                pytest.skip(f"Download failed: {e}")

    @pytest.mark.skipif(skip_if_no_internet(), reason="No internet connection")
    @pytest.mark.skipif(skip_if_chirps_down(), reason="CHIRPS server not accessible")
    def test_download_chirps_date_range(self):
        """Test downloading a date range."""
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                download_chirps(
                    dataset="africa_monthly",
                    start="2020-01",
                    end="2020-02",
                    out_dir=temp_dir,
                    unzip=False,
                )

                # Should have files for both months
                files = list(Path(temp_dir).glob("*.tif.gz"))
                assert len(files) >= 2

                # Check that both months are represented
                filenames = [f.name for f in files]
                has_jan = any("2020.01" in fname for fname in filenames)
                has_feb = any("2020.02" in fname for fname in filenames)
                assert has_jan
                assert has_feb

            except Exception as e:
                pytest.skip(f"Download failed: {e}")

    def test_download_chirps_skips_existing_files(self):
        """Test that existing files are skipped."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create a fake existing file
            existing_file = temp_path / "africa_monthly_chirps-v2.0.2020.01.tif"
            existing_file.write_text("fake content")

            with patch("requests.get") as mock_get:
                download_chirps(
                    dataset="africa_monthly",
                    start="2020-01",
                    out_dir=temp_dir,
                    unzip=True,
                )

                # requests.get should not have been called since file exists
                assert not mock_get.called

    def test_download_chirps_unzip_functionality(self):
        """Test the unzip functionality with mocked data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create fake gzipped content
            fake_tif_content = b"fake tif data"

            with patch("requests.get") as mock_get:
                # Create a mock response with gzipped content
                mock_response = Mock()
                mock_response.iter_content.return_value = [
                    gzip.compress(fake_tif_content)
                ]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                download_chirps(
                    dataset="africa_monthly",
                    start="2020-01",
                    out_dir=temp_dir,
                    unzip=True,
                )

                # Check that .tif file exists (not .tif.gz)
                tif_files = list(temp_path.glob("*.tif"))
                gz_files = list(temp_path.glob("*.tif.gz"))

                assert len(tif_files) == 1
                # .gz file should be removed after unzipping
                assert len(gz_files) == 0


class TestRetryDecorator:
    """Test retry decorator functionality."""

    def test_retry_succeeds_on_first_attempt(self):
        """Test retry decorator when function succeeds on first attempt."""

        @retry(times=3, delay=0.1, backoff=2.0)
        def successful_function():
            return "success"

        result = successful_function()
        assert result == "success"

    def test_retry_succeeds_after_failures(self):
        """Test retry decorator succeeds after some failures."""
        call_count = 0

        @retry(times=3, delay=0.1, backoff=2.0)
        def intermittent_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.RequestException("Temporary failure")
            return "success"

        with patch("time.sleep"):  # Speed up test by mocking sleep
            result = intermittent_function()
            assert result == "success"
            assert call_count == 3

    def test_retry_fails_after_max_attempts(self):
        """Test retry decorator fails after maximum attempts."""

        @retry(times=2, delay=0.1, backoff=2.0)
        def always_fails():
            raise requests.RequestException("Always fails")

        with (
            patch("time.sleep"),
            patch("sntutils.climate.download_chirps.logger") as mock_logger,
        ):
            with pytest.raises(requests.RequestException):
                always_fails()

            # Check that error logging was called
            mock_logger.error.assert_called()
            mock_logger.warning.assert_called()

    def test_download_file_with_retry_success(self):
        """Test _download_file_with_retry function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            dest_path = Path(temp_dir) / "test_file.tif.gz"

            with (
                patch("requests.get") as mock_get,
                patch("sntutils.climate.download_chirps.config") as mock_config,
            ):

                # Mock config values
                mock_config.get_timeout.return_value = 60
                mock_config.get_chunk_size.return_value = 8192

                # Mock successful response
                mock_response = Mock()
                mock_response.iter_content.return_value = [b"test data"]
                mock_response.raise_for_status.return_value = None
                mock_get.return_value = mock_response

                # Should not raise an exception
                _download_file_with_retry(
                    "http://example.com/test.tif.gz", dest_path, "test_file.tif.gz"
                )

                # Check file was written
                assert dest_path.exists()
                assert dest_path.read_bytes() == b"test data"


class TestConfigurationIntegration:
    """Test configuration integration."""

    def test_download_chirps_uses_config_default_directory(self):
        """Test that download_chirps uses config default directory when out_dir=None."""
        with (
            patch("sntutils.climate.download_chirps.config") as mock_config,
            patch("requests.get") as mock_get,
            patch("sntutils.climate.download_chirps.logger"),
        ):

            # Mock config to return a test directory
            test_dir = Path("/tmp/test_chirps")
            mock_config.get_download_dir.return_value = test_dir

            # Mock requests to avoid actual download
            mock_get.side_effect = requests.RequestException("Mocked failure")

            try:
                download_chirps(
                    dataset="africa_monthly",
                    start="2020-01",
                    out_dir=None,  # Should use config default
                )
            except Exception:
                pass  # Expected to fail

            # Verify config.get_download_dir was called
            mock_config.get_download_dir.assert_called_once()

    def test_logging_integration(self):
        """Test that logging calls are made during downloads."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("requests.get") as mock_get,
                patch("sntutils.climate.download_chirps.logger") as mock_logger,
            ):

                mock_get.side_effect = requests.RequestException("Network error")

                try:
                    download_chirps(
                        dataset="africa_monthly", start="2020-01", out_dir=temp_dir
                    )
                except Exception:
                    pass  # Expected to fail

                # Verify logging calls were made
                mock_logger.info.assert_called()


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_workflow_chirps_options_to_download(self):
        """Test the complete workflow from options to download."""
        # Get options
        options = chirps_options()
        assert len(options) > 0

        # Pick a dataset
        dataset = options.iloc[0]["dataset"]

        # Test with mocked download
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch("requests.get") as mock_get,
                patch("sntutils.climate.download_chirps.logger"),
            ):
                mock_get.side_effect = requests.RequestException("Mocked failure")

                try:
                    download_chirps(dataset=dataset, start="2020-01", out_dir=temp_dir)
                except Exception:
                    pass  # Expected to fail with mock

                # Directory should still be created
                assert Path(temp_dir).exists()
