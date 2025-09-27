"""
Tests for administrative names harmonization utilities.

Based on the R package testthat tests for harmonize_admin_names.R
"""

import os
import sys
import tempfile
import pickle
import unittest
from unittest import mock
from io import StringIO
import pandas as pd
import pytest
import numpy as np
from datetime import datetime

# Import the functions to test
from sntutils.geo.harmonize_admin_names import (
    handle_file_save,
    get_hierarchical_combinations,
    calculate_match_stats,
    format_choice,
    format_choices,
    display_custom_menu,
    calculate_string_distance,
    handle_user_interaction,
    construct_geo_names,
    apply_case_mapping,
    get_user_identity,
    export_unmatched_data,
    prep_geonames,
    impute_higher_admin,
)


class TestHandleFileSave:
    """Tests for handle_file_save function."""

    def test_handles_basic_file_saving(self, tmp_path):
        """Test basic file saving functionality."""
        test_file = tmp_path / "test_cache.pkl"
        test_data = pd.DataFrame({
            'level': [1, 2],
            'name_to_match': ['test1', 'test2'],
            'created_time': [datetime.now(), datetime.now()]
        })

        with mock.patch('builtins.input', side_effect=['y']):
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                handle_file_save(test_data, str(test_file))
                output = mock_stdout.getvalue()

        assert "File saved successfully" in output
        assert test_file.exists()

        # Check saved data
        with open(test_file, 'rb') as f:
            saved_data = pickle.load(f)
        assert len(saved_data) == 2
        assert list(saved_data['name_to_match']) == ['test1', 'test2']

    def test_merges_with_existing_cache(self, tmp_path):
        """Test merging with existing cache."""
        test_file = tmp_path / "test_cache.pkl"

        # Create existing cache
        existing_data = pd.DataFrame({
            'level': ['level0'],
            'name_to_match': ['existing'],
            'created_time': [datetime.now()]
        })

        with open(test_file, 'wb') as f:
            pickle.dump(existing_data, f)

        # New data to save
        new_data = pd.DataFrame({
            'level': ['level0', 'level0'],
            'name_to_match': ['new1', 'existing'],
            'created_time': [datetime.now(), datetime.now()]
        })

        with mock.patch('builtins.input', return_value='y'):
            with mock.patch('sys.stdout', new_callable=StringIO):
                handle_file_save(new_data, str(test_file))

        # Check merged results
        with open(test_file, 'rb') as f:
            merged_data = pickle.load(f)
        assert len(merged_data) == 2  # Should deduplicate
        assert 'new1' in merged_data['name_to_match'].values

    def test_handles_user_rejection(self):
        """Test handling user rejection."""
        with mock.patch('builtins.input', return_value='n'):
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                handle_file_save(pd.DataFrame())
                output = mock_stdout.getvalue()

        assert "File not saved" in output


class TestCalculateStringDistance:
    """Tests for calculate_string_distance function."""

    def test_works_correctly(self):
        """Test string distance calculation."""
        result = calculate_string_distance(
            ["New York", "Los Angeles"],
            ["New York", "Los Angeles", "Chicago"],
            "lv"
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 6  # 2 x 3 combinations
        assert 'algorithm_name' in result.columns
        assert 'distance' in result.columns
        assert 'match_rank' in result.columns

        # Check that exact matches have distance 0
        exact_matches = result[
            (result['name_to_match'] == 'New York') &
            (result['matched_names'] == 'New York')
        ]
        assert len(exact_matches) == 1
        assert exact_matches.iloc[0]['distance'] == 0


class TestCalculateMatchStats:
    """Tests for calculate_match_stats function."""

    def test_output_with_mock_data(self, capsys):
        """Test administrative matching stats output."""
        data = pd.DataFrame({
            'country': ['Country1', 'Country2', 'Country1', 'Country3'],
            'province': ['State1', 'State2', 'State1', 'State3'],
            'district': ['City1', 'City2', 'City1', 'City4']
        })

        lookup_data = pd.DataFrame({
            'country': ['Country1', 'Country2', 'Country1', 'Country3'],
            'province': ['State1', 'State2', 'State1', 'State3'],
            'district': ['City1', 'City2', 'City1', 'City4']
        })

        calculate_match_stats(
            data=data,
            lookup_data=lookup_data,
            level0='country',
            level1='province',
            level2='district',
            use_rich=False  # Use plain output for tests
        )

        captured = capsys.readouterr()
        assert "Match Summary" in captured.out

    def test_handles_empty_data(self, capsys):
        """Test handling of empty data."""
        empty_data = pd.DataFrame({
            'country': pd.Series(dtype=str),
            'province': pd.Series(dtype=str),
            'district': pd.Series(dtype=str)
        })

        lookup_data = pd.DataFrame({
            'country': ['USA', 'Canada'],
            'province': ['California', 'Ontario'],
            'district': ['Los Angeles', 'Toronto']
        })

        calculate_match_stats(
            data=empty_data,
            lookup_data=lookup_data,
            level0='country',
            level1='province',
            level2='district',
            use_rich=False  # Use plain output for tests
        )

        captured = capsys.readouterr()
        assert "0 out of 0 matched" in captured.out

    def test_ignores_case_in_matches(self, capsys):
        """Test that function ignores case in matches."""
        data = pd.DataFrame({
            'country': ['USA', 'canada', 'mexico']
        })

        lookup_data = pd.DataFrame({
            'country': ['usa', 'CANADA', 'France']
        })

        calculate_match_stats(
            data=data,
            lookup_data=lookup_data,
            level0='country',
            use_rich=False  # Use plain output for tests
        )

        captured = capsys.readouterr()
        assert "2 out of 3 matched" in captured.out


class TestFormatChoice:
    """Tests for format_choice function."""

    def test_formats_choices_correctly(self):
        """Test basic formatting."""
        assert format_choice(1, "Option A", 20) == "  1: Option A       "
        assert format_choice(10, "Option B", 20) == " 10: Option B       "
        assert format_choice(100, "Option C", 20) == "100: Option C       "

    def test_width_calculation(self):
        """Test width calculation."""
        result = format_choice(1, "Any text", 30)
        assert len(result) == 30

    def test_truncation_of_long_choices(self):
        """Test truncation of long choices."""
        long_choice = "This is a very long option that needs truncation"
        result = format_choice(5, long_choice, 25)

        assert len(result) == 25
        assert "..." in result

    def test_empty_choice(self):
        """Test empty choice."""
        result = format_choice(3, "", 10)
        assert result == "  3:      "


class TestFormatChoices:
    """Tests for format_choices function."""

    def test_single_column_display(self):
        """Test single column display formatting."""
        choices = ["Option A", "Option B", "Option C"]

        with mock.patch('sntutils.geo.harmonize_admin_names.format_choice',
                       side_effect=lambda idx, choice, width: f"{idx:3d}: {choice:<39}"):
            result = format_choices(choices, num_columns=1, column_width=45)

        assert isinstance(result, list)
        assert len(result) == 3  # One row per choice

    def test_multi_column_display(self):
        """Test multi-column display formatting."""
        choices = [f"Option {i}" for i in range(1, 7)]

        with mock.patch('sntutils.geo.harmonize_admin_names.format_choice',
                       side_effect=lambda idx, choice, width: f"{idx:3d}: {choice:<39}"):
            result = format_choices(choices, num_columns=2, column_width=45)

        assert isinstance(result, list)
        assert len(result) == 3  # 6 items in 2 columns = 3 rows


class TestDisplayCustomMenu:
    """Tests for display_custom_menu function."""

    def test_returns_correct_numeric_choice(self):
        """Test returning correct choice for numeric input."""
        with mock.patch('builtins.input', return_value='2'):
            with mock.patch('sys.stdout', new_callable=StringIO):
                result = display_custom_menu(
                    title="Select an option:",
                    main_header="Test Menu",
                    choices_input=["Option 1", "Option 2", "Option 3"],
                    special_actions={"x": "Exit", "q": "Quit"},
                    prompt="Your choice: "
                )

        assert result == '2'

    def test_returns_correct_special_action(self):
        """Test returning correct choice for special action."""
        with mock.patch('builtins.input', return_value='x'):
            with mock.patch('sys.stdout', new_callable=StringIO):
                result = display_custom_menu(
                    title="Select an option:",
                    main_header="Test Menu",
                    choices_input=["Option 1", "Option 2"],
                    special_actions={"x": "Exit", "q": "Quit"},
                    prompt="Your choice: "
                )

        assert result == 'x'

    def test_handles_invalid_then_valid_input(self):
        """Test handling invalid then valid input."""
        with mock.patch('builtins.input', side_effect=['invalid', '3']):
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = display_custom_menu(
                    title="Select an option:",
                    main_header="Test Menu",
                    choices_input=["Option 1", "Option 2", "Option 3"],
                    special_actions={"x": "Exit"},
                    prompt="Your choice: "
                )

        assert result == '3'
        assert "Invalid choice" in mock_stdout.getvalue()


class TestHandleUserInteraction:
    """Tests for handle_user_interaction function."""

    def test_processes_basic_selection(self):
        """Test processing basic selection correctly."""
        test_data = pd.DataFrame({
            'name_to_match': ['province1', 'province1', 'province2'],
            'matched_names': ['Province One', 'P1', 'Province Two'],
            'long_geo': ['country1', 'country1', 'country2']
        })

        with mock.patch('sntutils.geo.harmonize_admin_names.display_custom_menu',
                       side_effect=['1', '1']):
            with mock.patch('sys.stdout', new_callable=StringIO):
                with mock.patch('os.system'):
                    result = handle_user_interaction(
                        test_data,
                        levels=['country', 'province', 'district'],
                        level='province',
                        clear_console=False,
                        max_options=10
                    )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2  # One per unique name_to_match
        assert all(name in result['name_to_match'].values
                  for name in ['province1', 'province2'])

    def test_handles_manual_entry(self):
        """Test handling manual entry."""
        test_data = pd.DataFrame({
            'name_to_match': ['district1', 'district1'],
            'matched_names': ['District One', 'D1'],
            'long_geo': ['country1_province1', 'country1_province1']
        })

        with mock.patch('sntutils.geo.harmonize_admin_names.display_custom_menu',
                       return_value='m'):
            with mock.patch('builtins.input', return_value='Manual District'):
                with mock.patch('sys.stdout', new_callable=StringIO):
                    with mock.patch('os.system'):
                        result = handle_user_interaction(
                            test_data,
                            levels=['country', 'province', 'district'],
                            level='district',
                            clear_console=False,
                            max_options=10
                        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]['replacement'] == 'MANUAL DISTRICT'

    def test_handles_exit_without_saving(self):
        """Test handling exit without saving."""
        test_data = pd.DataFrame({
            'name_to_match': ['country1', 'country2'],
            'matched_names': ['Country One', 'Country Two'],
            'long_geo': ['country1', 'country2']
        })

        with mock.patch('sntutils.geo.harmonize_admin_names.display_custom_menu',
                       return_value='q'):
            with mock.patch('builtins.input', return_value='y'):
                with mock.patch('sys.stdout', new_callable=StringIO):
                    with mock.patch('os.system'):
                        result = handle_user_interaction(
                            test_data,
                            levels=['country', 'province'],
                            level='country',
                            clear_console=False,
                            max_options=10
                        )

        assert result is None


class TestPrepGeonames:
    """Tests for prep_geonames function."""

    def test_correctly_processes_admin_names(self):
        """Test that prep_geonames correctly processes admin names."""
        target_df = pd.DataFrame({
            'country': ['ANGOLA', 'UGA', 'ZAMBIA'],
            'province': ['CABONDA', 'TESO', 'LUSAKA'],
            'district': ['BALIZE', 'BOKEDEA', 'RAFUNSA'],
            'subdistrict': ['AREA1', 'AREA2', 'AREA3']
        })

        with mock.patch('sys.stdout', new_callable=StringIO):
            cleaned_df = prep_geonames(
                target_df,
                level0='country',
                level1='province',
                level2='district',
                interactive=False
            )

        assert isinstance(cleaned_df, pd.DataFrame)
        assert len(cleaned_df) == len(target_df)
        assert all(col in cleaned_df.columns
                  for col in ['country', 'province', 'district', 'subdistrict'])

    def test_validates_inputs_correctly(self):
        """Test input validation."""
        target_df = pd.DataFrame({
            'country': ['ANGOLA', 'UGANDA'],
            'region': ['CABINDA', 'TESO']  # Not matching the level1 name
        })

        lookup_df = pd.DataFrame({
            'country': ['ANGOLA', 'UGANDA'],
            'province': ['CABINDA', 'TESO']  # Uses province instead of region
        })

        with pytest.raises(ValueError, match="missing in target_df"):
            prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='country',
                level1='province',  # This column doesn't exist in target_df
                interactive=False
            )

        # Test unsupported method
        with pytest.raises(ValueError, match="Unsupported method"):
            prep_geonames(
                target_df=pd.DataFrame({'country': ['ANGOLA']}),
                level0='country',
                method='invalid_method',
                interactive=False
            )

    def test_handles_level_hierarchies(self):
        """Test handling of level hierarchies."""
        target_df = pd.DataFrame({
            'country': ['ANGOLA'],
            'province': ['CABINDA'],
            'district': ['BUCO-ZAU']
        })

        # Should error if specifying level2 without level0 and level1
        with pytest.raises(ValueError, match="cannot specify level2"):
            prep_geonames(
                target_df=target_df,
                level2='district',  # Missing level0 and level1
                interactive=False
            )

        # Should error if specifying level1 without level0
        with pytest.raises(ValueError, match="cannot specify level1"):
            prep_geonames(
                target_df=target_df,
                level1='province',  # Missing level0
                interactive=False
            )

    def test_handles_case_conversion(self):
        """Test case conversion handling."""
        target_df = pd.DataFrame({
            'country': ['angola', 'Uganda']
        })

        lookup_df = pd.DataFrame({
            'country': ['ANGOLA', 'UGANDA']
        })

        with mock.patch('sys.stdout', new_callable=StringIO):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='country',
                interactive=False
            )

        # Check that names were converted to uppercase
        assert list(result['country']) == ['ANGOLA', 'UGANDA']

    def test_handles_missing_data(self):
        """Test handling of missing data."""
        target_df = pd.DataFrame({
            'country': ['ANGOLA', 'UGANDA', np.nan],
            'province': ['CABINDA', np.nan, np.nan]
        })

        lookup_df = pd.DataFrame({
            'country': ['ANGOLA', 'UGANDA'],
            'province': ['CABINDA', 'TESO']
        })

        with mock.patch('sys.stdout', new_callable=StringIO):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='country',
                level1='province',
                interactive=False
            )

        # Verify NA values are preserved
        assert pd.isna(result.iloc[2]['country'])
        assert pd.isna(result.iloc[1]['province'])
        assert pd.isna(result.iloc[2]['province'])

    def test_preserve_case_feature(self):
        """Test preserve_case feature."""
        target_df = pd.DataFrame({
            'country': ['KENYA', 'KENYA', 'UGANDA'],
            'province': ['NAIROBI', 'COAST', 'KAMPALA']
        })

        lookup_df = pd.DataFrame({
            'country': ['Kenya', 'Kenya', 'Uganda'],
            'province': ['Nairobi', 'Coast', 'Kampala']
        })

        # Test with preserve_case = False (default)
        with mock.patch('sys.stdout', new_callable=StringIO):
            result_uppercase = prep_geonames(
                target_df,
                lookup_df=lookup_df,
                level0='country',
                level1='province',
                interactive=False,
                preserve_case=False
            )

        # Should return uppercase
        assert result_uppercase.iloc[0]['country'] == 'KENYA'
        assert result_uppercase.iloc[0]['province'] == 'NAIROBI'

        # Test with preserve_case = True
        with mock.patch('sys.stdout', new_callable=StringIO):
            result_preserved = prep_geonames(
                target_df,
                lookup_df=lookup_df,
                level0='country',
                level1='province',
                interactive=False,
                preserve_case=True
            )

        # Should return original case from lookup
        assert result_preserved.iloc[0]['country'] == 'Kenya'
        assert result_preserved.iloc[0]['province'] == 'Nairobi'

    def test_unmatched_export_path(self, tmp_path):
        """Test unmatched_export_path feature."""
        test_target = pd.DataFrame({
            'country': ['KENYA', 'KENYA', 'KENYA', 'TANZANIA'],
            'province': ['NAIROBI', 'COAST', 'UNKNOWN_PROVINCE', 'DAR'],
            'district': ['WESTLANDS', 'MOMBASA', 'UNKNOWN_DISTRICT', 'ILALA']
        })

        test_lookup = pd.DataFrame({
            'country': ['KENYA', 'KENYA'],
            'province': ['NAIROBI', 'COAST'],
            'district': ['WESTLANDS', 'MOMBASA']
        })

        # Test CSV export
        csv_path = tmp_path / "unmatched.csv"

        with mock.patch('sys.stdout', new_callable=StringIO):
            result = prep_geonames(
                test_target,
                lookup_df=test_lookup,
                level0='country',
                level1='province',
                level2='district',
                interactive=False,
                unmatched_export_path=str(csv_path)
            )

        # Check that file was created
        assert csv_path.exists()

        # Read and check the exported data
        exported_data = pd.read_csv(csv_path)

        # Check structure
        assert 'unmatched_column' in exported_data.columns
        assert 'country' in exported_data.columns
        assert 'province' in exported_data.columns
        assert 'district' in exported_data.columns
        assert 'target_data' in exported_data.columns
        assert 'lookup_data' in exported_data.columns


class TestImputeHigherAdmin:
    """Tests for impute_higher_admin function."""

    def test_works_correctly(self):
        """Test basic functionality."""
        lookup = pd.DataFrame({
            'district': ['Boffa', 'Boke', 'Fria'],
            'region': ['Boké', 'Boké', 'Boké']
        })

        test_data = pd.DataFrame({
            'location': ['Boffa', 'Fria', 'Unknown']
        })

        result = impute_higher_admin(
            target_df=test_data,
            target_lower_col='location',
            target_higher_col='region',
            lookup_df=lookup,
            lookup_lower_col='district',
            lookup_higher_col='region'
        )

        assert list(result['region']) == ['Boké', 'Boké', 'Unknown']
        assert len(result.columns) == 2

    def test_handles_empty_dataframe(self):
        """Test with empty dataframe."""
        lookup = pd.DataFrame({
            'district': ['Boffa'],
            'region': ['Boké']
        })

        empty_data = pd.DataFrame({'location': pd.Series(dtype=str)})

        result = impute_higher_admin(
            target_df=empty_data,
            target_lower_col='location',
            target_higher_col='region',
            lookup_df=lookup,
            lookup_lower_col='district',
            lookup_higher_col='region'
        )

        assert len(result) == 0
        assert len(result.columns) == 2


class TestConstructGeoNames:
    """Tests for construct_geo_names function."""

    def test_creates_long_geo_correctly(self):
        """Test that long_geo is created correctly."""
        data = pd.DataFrame({
            'country': ['USA', 'USA', 'Canada'],
            'state': ['California', None, 'Ontario'],
            'city': ['Los Angeles', 'New York', 'Toronto'],
            'subdistrict': ['Downtown', 'Manhattan', 'Scarborough']
        })

        result = construct_geo_names(
            data, 'country', 'state', 'city', 'subdistrict'
        )

        assert 'long_geo' in result.columns
        assert result.iloc[0]['long_geo'] == 'USA_California_Los Angeles_Downtown'
        assert result.iloc[1]['long_geo'] == 'USA_New York_Manhattan'  # Skips None
        assert result.iloc[2]['long_geo'] == 'Canada_Ontario_Toronto_Scarborough'


class TestGetHierarchicalCombinations:
    """Tests for get_hierarchical_combinations function."""

    def test_returns_unique_combinations(self):
        """Test that unique combinations are returned."""
        df = pd.DataFrame({
            'country': ['A', 'A', 'B'],
            'province': ['P1', 'P2', 'P1'],
            'district': ['D1', 'D1', 'D2']
        })

        result = get_hierarchical_combinations(
            df, ['country', 'province', 'district']
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 3  # All three rows are unique combinations

    def test_excludes_rows_with_na(self):
        """Test that rows with NA values are excluded."""
        df = pd.DataFrame({
            'country': ['A', None, 'B'],
            'province': ['P1', 'P2', None]
        })

        result = get_hierarchical_combinations(df, ['country', 'province'])

        assert len(result) == 1  # Only first row has no NAs


class TestInteractiveMatching:
    """Tests for interactive matching functionality including special menu options."""

    def test_skip_option(self):
        """Test that Skip (S) option skips the current item without replacement."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria'],
            'adm1': ['FCT-ABUJA', 'KAYNO']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 4,
            'adm1': ['FCT, ABUJA', 'KANO', 'LAGOS', 'OYO']
        })

        # Mock user input: skip both items
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 's', 's', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            # Should return result but without replacements
            assert result is not None
            assert 'FCT-ABUJA' in result['adm1'].values
            assert 'KAYNO' in result['adm1'].values

    def test_manual_entry_option(self):
        """Test that Manual entry (M) option allows custom replacement names."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['FCT-ABUJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 3,
            'adm1': ['KANO', 'LAGOS', 'OYO']
        })

        # Mock user input: enter manual name
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 'm', 'Federal Capital Territory', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            assert result is not None
            # Manual entry should be uppercased
            assert 'FEDERAL CAPITAL TERRITORY' in result['adm1'].values

    def test_go_back_option(self):
        """Test that Go Back (B) option allows revisiting previous choices."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria'],
            'adm1': ['FCT-ABUJA', 'KAYNO']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 4,
            'adm1': ['FCT, ABUJA', 'KANO', 'LAGOS', 'OYO']
        })

        # Mock user input: skip first, go back, then select option 1
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 's', 'b', '1', 's', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            assert result is not None
            # First item should have been replaced after going back
            assert 'FCT, ABUJA' in result['adm1'].values

    def test_save_and_exit_option(self):
        """Test that Save and exit (E) option saves choices and exits early."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria', 'Nigeria'],
            'adm1': ['FCT-ABUJA', 'KAYNO', 'OYOO']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 4,
            'adm1': ['FCT, ABUJA', 'KANO', 'LAGOS', 'OYO']
        })

        # Mock user input: select first option, then save and exit
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', 'e', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            assert result is not None
            # Only first item should be replaced before exit
            assert 'FCT, ABUJA' in result['adm1'].values
            # Other items remain unchanged
            assert 'KAYNO' in result['adm1'].values
            assert 'OYOO' in result['adm1'].values

    def test_exit_without_saving_option(self):
        """Test that Exit without saving (Q) option exits without making changes."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['FCT-ABUJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 3,
            'adm1': ['FCT, ABUJA', 'KANO', 'LAGOS']
        })

        # Mock user input: try exit without saving (with confirmation)
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 'q', 'y', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            assert result is not None
            # Original value should remain unchanged
            assert 'FCT-ABUJA' in result['adm1'].values

    def test_exit_without_saving_cancelled(self):
        """Test that cancelling Exit without saving returns to menu."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['FCT-ABUJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 3,
            'adm1': ['FCT, ABUJA', 'KANO', 'LAGOS']
        })

        # Mock user input: try to exit, cancel, then select option 1
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 'q', 'n', '1', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            assert result is not None
            # Should have made the replacement after cancelling exit
            assert 'FCT, ABUJA' in result['adm1'].values

    def test_numeric_selection(self):
        """Test that numeric selections work correctly."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['UNKNOWN_STATE']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 5,
            'adm1': ['LAGOS', 'KANO', 'RIVERS', 'OYO', 'KADUNA']
        })

        # Mock user input: select option 5 (RIVERS based on fuzzy match order)
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '5', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True
            )

            assert result is not None
            assert 'RIVERS' in result['adm1'].values

    def test_multiple_options_displayed(self):
        """Test that multiple matching options are displayed, not just the best match."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['ABUJA_FCT']  # Different format that should show multiple options
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 10,
            'adm1': ['FCT, ABUJA', 'ABUJA', 'LAGOS', 'KANO', 'RIVERS',
                    'OYO', 'KADUNA', 'ENUGU', 'IMO', 'DELTA']
        })

        # The calculate_string_distance should return all options
        admins_to_clean = ['ABUJA_FCT']
        lookup_admins = lookup_df['adm1'].unique().tolist()

        result = calculate_string_distance(admins_to_clean, lookup_admins, method='jw')

        # Should have matches for all lookup options
        assert len(result) == len(lookup_admins)
        # Results should be sorted by distance
        assert result['distance'].is_monotonic_increasing or (result.groupby('name_to_match')['distance'].transform(lambda x: x.is_monotonic_increasing).all())

    def test_hierarchical_matching(self):
        """Test hierarchical matching for adm2 within adm1."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria'],
            'adm1': ['LAGOS', 'LAGOS'],
            'adm2': ['IKEJA_WRONG', 'LAGOS_ISLAND_WRONG']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 6,
            'adm1': ['LAGOS', 'LAGOS', 'LAGOS', 'KANO', 'KANO', 'KANO'],
            'adm2': ['IKEJA', 'LAGOS ISLAND', 'SURULERE', 'KANO MUNICIPAL', 'FAGGE', 'DALA']
        })

        # Mock user input: select correct matches for Lagos districts only
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', '1', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                level2='adm2',
                interactive=True
            )

            assert result is not None
            # Should match to Lagos districts, not Kano districts
            assert 'IKEJA' in result['adm2'].values
            assert 'LAGOS ISLAND' in result['adm2'].values
            assert 'KANO MUNICIPAL' not in result['adm2'].values

    def test_max_options_parameter(self):
        """Test that max_options parameter limits displayed choices."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['UNKNOWN']
        })

        # Create many lookup options
        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 50,
            'adm1': [f'STATE_{i}' for i in range(50)]
        })

        # Test with limited max_options
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 's', 'n', 'n']):
            # Note: max_options affects display, internally it should handle this
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                interactive=True,
                max_options=10  # Limit to 10 options
            )

            assert result is not None

    def test_invalid_input_handling(self):
        """Test that invalid inputs are handled gracefully."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['FCT-ABUJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 3,
            'adm1': ['FCT, ABUJA', 'KANO', 'LAGOS']
        })

        # Mock user input: invalid inputs followed by valid ones
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 'invalid', 'xyz', '99', '1', 'n', 'n']):
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = prep_geonames(
                    target_df=target_df,
                    lookup_df=lookup_df,
                    level0='adm0',
                    level1='adm1',
                    interactive=True
                )

                output = mock_stdout.getvalue()
                assert 'Invalid choice' in output
                assert result is not None
                # Should eventually accept valid input
                assert 'FCT, ABUJA' in result['adm1'].values

    def test_empty_manual_entry(self):
        """Test that empty manual entry returns to menu."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['FCT-ABUJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 3,
            'adm1': ['KANO', 'LAGOS', 'OYO']
        })

        # Mock user input: empty manual entry, then valid selection
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 'm', '', '1', 'n', 'n']):
            with mock.patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                result = prep_geonames(
                    target_df=target_df,
                    lookup_df=lookup_df,
                    level0='adm0',
                    level1='adm1',
                    interactive=True
                )

                output = mock_stdout.getvalue()
                assert 'No name entered' in output


class TestCacheHandling(unittest.TestCase):
    """Test cache structure and save/load functionality."""

    def setUp(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.temp_dir, 'test_cache.xlsx')

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cache_structure_saved(self):
        """Test that cache is saved with correct column structure."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria'],
            'adm1': ['FCT-ABUJA', 'LAGOS'],
            'adm2': ['ABUJA MUNICIPAL', 'IKEJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 6,
            'adm1': ['FCT, ABUJA', 'FCT, ABUJA', 'LAGOS', 'LAGOS', 'KANO', 'KANO'],
            'adm2': ['ABUJA MUNICIPAL', 'BWARI', 'IKEJA', 'SURULERE', 'KANO MUNICIPAL', 'FAGGE']
        })

        # Mock user input: match FCT-ABUJA to FCT, ABUJA and save cache
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', '1', '1', '1', 'y']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                level2='adm2',
                cache_path=self.cache_path,
                interactive=True
            )

        # Check cache was created and has correct structure
        self.assertTrue(os.path.exists(self.cache_path))

        # Load and verify cache structure
        cache_df = pd.read_excel(self.cache_path)

        # Required columns
        required_cols = ['level', 'name_to_match', 'replacement',
                        'level0_prepped', 'level1_prepped', 'level2_prepped',
                        'level3_prepped', 'level4_prepped',
                        'created_time', 'name_of_creator']
        for col in required_cols:
            self.assertIn(col, cache_df.columns, f"Missing column: {col}")

        # Should NOT have longname_to_match (it's reconstructed on load)
        self.assertNotIn('longname_to_match', cache_df.columns)
        self.assertNotIn('longname_corrected', cache_df.columns)

        # Check hierarchical columns are populated correctly
        level1_cache = cache_df[cache_df['level'] == 'level1']
        if not level1_cache.empty:
            # level0_prepped should be NIGERIA for level1 entries
            self.assertEqual(level1_cache.iloc[0]['level0_prepped'], 'NIGERIA')
            # level1_prepped should be the replacement value
            self.assertEqual(level1_cache.iloc[0]['level1_prepped'], level1_cache.iloc[0]['replacement'])

    def test_cache_load_and_apply(self):
        """Test that cached corrections are loaded and applied correctly."""
        # Create a cache file with some corrections
        cache_data = pd.DataFrame({
            'level': ['level0', 'level1', 'level1'],
            'name_to_match': ['Nigeria', 'FCT-ABUJA', 'KAYNO'],
            'replacement': ['NIGERIA', 'FCT, ABUJA', 'KANO'],
            'level0_prepped': ['NIGERIA', 'NIGERIA', 'NIGERIA'],
            'level1_prepped': [None, 'FCT, ABUJA', 'KANO'],
            'level2_prepped': [None, None, None],
            'level3_prepped': [None, None, None],
            'level4_prepped': [None, None, None],
            'created_time': [datetime.now()] * 3,
            'name_of_creator': ['test_user'] * 3
        })
        cache_data.to_excel(self.cache_path, index=False)

        # New data with same mismatches
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria', 'Nigeria'],
            'adm1': ['FCT-ABUJA', 'KAYNO', 'LAGOS'],
            'adm2': ['ABUJA MUNICIPAL', 'KANO MUNICIPAL', 'IKEJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 9,
            'adm1': ['FCT, ABUJA', 'FCT, ABUJA', 'FCT, ABUJA',
                    'KANO', 'KANO', 'KANO',
                    'LAGOS', 'LAGOS', 'LAGOS'],
            'adm2': ['ABUJA MUNICIPAL', 'BWARI', 'KUJE',
                    'KANO MUNICIPAL', 'FAGGE', 'DALA',
                    'IKEJA', 'SURULERE', 'LAGOS ISLAND']
        })

        # Run with cache (non-interactive since corrections are cached)
        result = prep_geonames(
            target_df=target_df,
            lookup_df=lookup_df,
            level0='adm0',
            level1='adm1',
            level2='adm2',
            cache_path=self.cache_path,
            interactive=False
        )

        # Check that cached corrections were applied
        self.assertIn('FCT, ABUJA', result['adm1'].values)
        self.assertIn('KANO', result['adm1'].values)
        # Lagos should remain unchanged
        self.assertIn('LAGOS', result['adm1'].values)

    def test_cache_merge_with_existing(self):
        """Test that new corrections are merged with existing cache."""
        # Create initial cache
        initial_cache = pd.DataFrame({
            'level': ['level1'],
            'name_to_match': ['FCT-ABUJA'],
            'replacement': ['FCT, ABUJA'],
            'level0_prepped': ['NIGERIA'],
            'level1_prepped': ['FCT, ABUJA'],
            'level2_prepped': [None],
            'level3_prepped': [None],
            'level4_prepped': [None],
            'created_time': [datetime.now()],
            'name_of_creator': ['initial_user']
        })
        initial_cache.to_excel(self.cache_path, index=False)

        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['KAYNO']  # Different mismatch
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 3,
            'adm1': ['KANO', 'LAGOS', 'FCT, ABUJA']
        })

        # Mock user input to add new correction
        with mock.patch('builtins.input', side_effect=['yes', '1', 'y']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                cache_path=self.cache_path,
                interactive=True
            )

        # Load merged cache
        merged_cache = pd.read_excel(self.cache_path)

        # Should have both corrections
        self.assertEqual(len(merged_cache), 2)
        self.assertIn('FCT-ABUJA', merged_cache['name_to_match'].values)
        self.assertIn('KAYNO', merged_cache['name_to_match'].values)

    def test_cache_formats(self):
        """Test cache works with different file formats."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'],
            'adm1': ['FCT-ABUJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 2,
            'adm1': ['FCT, ABUJA', 'LAGOS']
        })

        # Test CSV format
        csv_cache = os.path.join(self.temp_dir, 'cache.csv')
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', 'y']):
            result = prep_geonames(
                target_df=target_df.copy(),
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                cache_path=csv_cache,
                interactive=True
            )
        self.assertTrue(os.path.exists(csv_cache))

        # Test pickle format
        pkl_cache = os.path.join(self.temp_dir, 'cache.pkl')
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', 'y']):
            result = prep_geonames(
                target_df=target_df.copy(),
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                cache_path=pkl_cache,
                interactive=True
            )
        self.assertTrue(os.path.exists(pkl_cache))


class TestUnmatchedDataHandling(unittest.TestCase):
    """Test unmatched data export and handling."""

    def setUp(self):
        """Set up test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.unmatched_path = os.path.join(self.temp_dir, 'unmatched.xlsx')

    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unmatched_export(self):
        """Test that unmatched data is exported correctly."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria', 'Nigeria'],
            'adm1': ['FCT-ABUJA', 'UNKNOWN_STATE', 'LAGOS'],
            'adm2': ['ABUJA MUNICIPAL', 'UNKNOWN_LGA', 'IKEJA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 6,
            'adm1': ['FCT, ABUJA', 'FCT, ABUJA', 'LAGOS', 'LAGOS', 'KANO', 'KANO'],
            'adm2': ['ABUJA MUNICIPAL', 'BWARI', 'IKEJA', 'SURULERE', 'KANO MUNICIPAL', 'FAGGE']
        })

        # Run with unmatched export
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', 's', '1', '1', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                level2='adm2',
                unmatched_export_path=self.unmatched_path,
                interactive=True
            )

        # Check unmatched file was created
        self.assertTrue(os.path.exists(self.unmatched_path))

        # Load and verify unmatched data
        unmatched_df = pd.read_excel(self.unmatched_path)

        # Should contain UNKNOWN_STATE row
        self.assertIn('UNKNOWN_STATE', unmatched_df['adm1'].values)
        self.assertIn('UNKNOWN_LGA', unmatched_df['adm2'].values)

        # Should have metadata columns
        self.assertIn('target_data', unmatched_df.columns)
        self.assertIn('lookup_data', unmatched_df.columns)

    def test_hierarchical_unmatched(self):
        """Test unmatched handling in hierarchical matching."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria', 'Nigeria'],
            'adm1': ['UNKNOWN_STATE', 'UNKNOWN_STATE'],
            'adm2': ['SOME_LGA', 'ANOTHER_LGA']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 4,
            'adm1': ['LAGOS', 'LAGOS', 'KANO', 'KANO'],
            'adm2': ['IKEJA', 'SURULERE', 'KANO MUNICIPAL', 'FAGGE']
        })

        # Run - should skip adm2 matching since adm1 doesn't match
        with mock.patch('builtins.input', side_effect=['yes', 'yes', 's', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                level2='adm2',
                unmatched_export_path=self.unmatched_path,
                interactive=True
            )

        # All rows should remain unmatched
        self.assertEqual(len(result[result['adm1'] == 'UNKNOWN_STATE']), 2)

        # Unmatched export should contain both rows
        if os.path.exists(self.unmatched_path):
            unmatched_df = pd.read_excel(self.unmatched_path)
            self.assertEqual(len(unmatched_df), 2)

    def test_partial_matching(self):
        """Test when some items match and others don't."""
        target_df = pd.DataFrame({
            'adm0': ['Nigeria'] * 5,
            'adm1': ['LAGOS', 'KANO', 'UNKNOWN1', 'UNKNOWN2', 'FCT-ABUJA'],
            'adm2': ['IKEJA', 'KANO MUNICIPAL', 'LGA1', 'LGA2', 'ABUJA MUNICIPAL']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['NIGERIA'] * 8,
            'adm1': ['LAGOS', 'LAGOS', 'KANO', 'KANO',
                    'FCT, ABUJA', 'FCT, ABUJA', 'RIVERS', 'RIVERS'],
            'adm2': ['IKEJA', 'SURULERE', 'KANO MUNICIPAL', 'FAGGE',
                    'ABUJA MUNICIPAL', 'BWARI', 'PORT HARCOURT', 'OBIO-AKPOR']
        })

        # Run with some matches
        with mock.patch('builtins.input', side_effect=['yes', 'yes', '1', 's', 's', 'n', 'n']):
            result = prep_geonames(
                target_df=target_df,
                lookup_df=lookup_df,
                level0='adm0',
                level1='adm1',
                level2='adm2',
                unmatched_export_path=self.unmatched_path,
                interactive=True
            )

        # Check matched items
        self.assertIn('LAGOS', result['adm1'].values)
        self.assertIn('KANO', result['adm1'].values)
        self.assertIn('FCT, ABUJA', result['adm1'].values)

        # Check unmatched items
        self.assertIn('UNKNOWN1', result['adm1'].values)
        self.assertIn('UNKNOWN2', result['adm1'].values)

        # Verify unmatched export
        if os.path.exists(self.unmatched_path):
            unmatched_df = pd.read_excel(self.unmatched_path)
            self.assertIn('UNKNOWN1', unmatched_df['adm1'].values)
            self.assertIn('UNKNOWN2', unmatched_df['adm1'].values)


class TestPreserveCaseFeature(unittest.TestCase):
    """Test preserve_case functionality."""

    def test_preserve_case_from_lookup(self):
        """Test that original casing is preserved from lookup data."""
        target_df = pd.DataFrame({
            'adm0': ['NIGERIA'],
            'adm1': ['lagos'],
            'adm2': ['ikeja']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['Nigeria'] * 3,
            'adm1': ['Lagos', 'Kano', 'Rivers'],
            'adm2': ['Ikeja', 'Kano Municipal', 'Port Harcourt']
        })

        # Run with preserve_case=True
        result = prep_geonames(
            target_df=target_df,
            lookup_df=lookup_df,
            level0='adm0',
            level1='adm1',
            level2='adm2',
            preserve_case=True,
            interactive=False
        )

        # Check that original casing from lookup is preserved
        self.assertIn('Lagos', result['adm1'].values)
        self.assertIn('Ikeja', result['adm2'].values)
        self.assertNotIn('LAGOS', result['adm1'].values)
        self.assertNotIn('IKEJA', result['adm2'].values)

    def test_no_preserve_case(self):
        """Test that uppercase is used when preserve_case=False."""
        target_df = pd.DataFrame({
            'adm0': ['nigeria'],
            'adm1': ['lagos']
        })

        lookup_df = pd.DataFrame({
            'adm0': ['Nigeria'] * 2,
            'adm1': ['Lagos', 'Kano']
        })

        # Run with preserve_case=False
        result = prep_geonames(
            target_df=target_df,
            lookup_df=lookup_df,
            level0='adm0',
            level1='adm1',
            preserve_case=False,
            interactive=False
        )

        # Check that uppercase is used
        self.assertIn('LAGOS', result['adm1'].values)
        self.assertNotIn('Lagos', result['adm1'].values)