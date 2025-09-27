"""
Administrative names harmonization utilities.

This module provides functions for cleaning and standardizing administrative
geographic names (country, province, district, etc.) by matching them against
reference lookup data.
"""

import os
import sys
import warnings
import getpass
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any
from datetime import datetime
import numpy as np
import pandas as pd
from io import StringIO

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.theme import Theme
    from rich import box
    from rich.columns import Columns
    from rich.align import Align

    # Create custom theme for admin name harmonization
    theme = Theme({
        "success": "bold green",
        "info": "bold cyan",
        "warning": "bold yellow",
        "error": "bold red",
        "primary": "bold blue",
        "muted": "dim white",
        "highlight": "bold white",
    })
    console = Console(theme=theme)
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    console = None

try:
    from stringdist import levenshtein, jaro_winkler
except ImportError:
    import Levenshtein
    def levenshtein(s1, s2):
        return Levenshtein.distance(s1, s2)
    def jaro_winkler(s1, s2):
        return 1 - Levenshtein.jaro_winkler(s1, s2)


def handle_file_save(
    data_to_save: pd.DataFrame,
    default_save_path: Optional[str] = None
) -> None:
    """
    Save DataFrame to RDS/pickle file with user confirmation.

    Prompts the user for confirmation before saving a dataframe to a file.
    If the specified file path does not exist or is None, the user is prompted
    to provide a new path. If a cache file already exists, the function merges
    new data with existing data, ensuring that the most recent entries are retained.

    Parameters
    ----------
    data_to_save : pd.DataFrame
        DataFrame to be saved.
    default_save_path : str, optional
        Default path for saving the dataframe. If not provided or invalid,
        the user is prompted for a new path.

    Returns
    -------
    None
        The function's primary purpose is saving a file, not returning a value.
    """
    cache_path = default_save_path

    while True:
        confirm_save = input("Do you want to save the cleaned cache file? [y/n]: ").lower()

        if confirm_save == "y":
            # Validate or set a default cache path
            if cache_path is None or os.path.isdir(cache_path):
                print("Warning: The specified path is null or is a directory.")

                cache_path = input("Enter the new file path (including filename) for saving: ")

                if cache_path == "" or os.path.isdir(cache_path):
                    cache_path = os.path.join(os.getcwd(), "prepped_geoname_cache.pkl")
                    print(f"Info: No valid path provided. Using default: {cache_path}")

            # Ensure parent directory exists
            cache_dir = os.path.dirname(cache_path)
            if cache_dir and not os.path.exists(cache_dir):
                os.makedirs(cache_dir, exist_ok=True)

            # Ensure we are working with a file, not a directory
            if os.path.isdir(cache_path):
                raise ValueError("`cache_path` should be a file path, not a directory.")

            # Load existing cache if available
            existing_cache = None
            if os.path.exists(cache_path):
                try:
                    with open(cache_path, 'rb') as f:
                        existing_cache = pickle.load(f)
                except:
                    existing_cache = None

            # Merge with existing cache if applicable
            if existing_cache is not None and len(existing_cache) > 0:
                merged_cache = pd.concat([existing_cache, data_to_save], ignore_index=True)
                merged_cache = (merged_cache
                    .sort_values('created_time', ascending=False)
                    .drop_duplicates(subset=['level', 'name_to_match'], keep='first'))
            else:
                merged_cache = data_to_save

            # Save the merged cache based on file extension
            cache_ext = Path(cache_path).suffix.lower()
            if cache_ext in ['.xlsx', '.xls']:
                merged_cache.to_excel(cache_path, index=False)
            elif cache_ext == '.csv':
                merged_cache.to_csv(cache_path, index=False)
            else:
                # Default to pickle
                with open(cache_path, 'wb') as f:
                    pickle.dump(merged_cache, f)
            print(f"Success: File saved successfully to {cache_path}.")
            break

        elif confirm_save == "n":
            print("Info: File not saved. Proceeding without saving...")
            break
        else:
            print("Warning: Invalid input. Please respond with 'y' or 'n'.")


def export_dataframe(
    df: pd.DataFrame,
    file_path: str,
    format: Optional[str] = None
) -> bool:
    """
    Export DataFrame to various formats including RDS (for R), Excel, CSV, Parquet, etc.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame to export.
    file_path : str
        Output file path.
    format : str, optional
        Output format. If None, inferred from file extension.
        Supported: 'csv', 'xlsx', 'xls', 'parquet', 'pickle', 'rds', 'json', 'feather'

    Returns
    -------
    bool
        True if export successful, False otherwise.
    """
    # Infer format from extension if not specified
    if format is None:
        file_ext = Path(file_path).suffix.lower()
        format = file_ext.lstrip('.')
    else:
        format = format.lower()

    # Ensure directory exists
    output_dir = os.path.dirname(file_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    try:
        if format in ['csv', 'txt']:
            df.to_csv(file_path, index=False)
            print(f"✓ Data exported to CSV: {file_path}")

        elif format in ['xlsx', 'xls']:
            # Check if openpyxl is available
            try:
                import openpyxl
                df.to_excel(file_path, index=False, engine='openpyxl')
                print(f"✓ Data exported to Excel: {file_path}")
            except ImportError:
                print("Warning: openpyxl not installed. Install with: pip install openpyxl")
                return False

        elif format == 'parquet':
            # Check if pyarrow or fastparquet is available
            try:
                df.to_parquet(file_path, index=False)
                print(f"✓ Data exported to Parquet: {file_path}")
            except ImportError:
                print("Warning: pyarrow or fastparquet not installed. Install with: pip install pyarrow")
                return False

        elif format in ['pickle', 'pkl']:
            with open(file_path, 'wb') as f:
                pickle.dump(df, f)
            print(f"✓ Data exported to Pickle: {file_path}")

        elif format == 'rds':
            # For RDS format, we'll use a special approach
            # RDS is R's native format, so we'll create a pickle file with metadata
            # that can be easily read in R using reticulate or converted
            try:
                import pyreadr
                pyreadr.write_rds(file_path, df)
                print(f"✓ Data exported to RDS: {file_path}")
            except ImportError:
                # Fallback: save as pickle with RDS extension and metadata
                rds_data = {
                    'data': df,
                    'format': 'python_rds_compatible',
                    'created': datetime.now().isoformat(),
                    'shape': df.shape,
                    'columns': df.columns.tolist(),
                    'dtypes': df.dtypes.astype(str).to_dict()
                }
                with open(file_path, 'wb') as f:
                    pickle.dump(rds_data, f)
                print(f"✓ Data exported to RDS-compatible format: {file_path}")
                print("  Note: Use Python or reticulate in R to read this file")

        elif format == 'json':
            df.to_json(file_path, orient='records', indent=2)
            print(f"✓ Data exported to JSON: {file_path}")

        elif format == 'feather':
            # Check if pyarrow is available
            try:
                df.to_feather(file_path)
                print(f"✓ Data exported to Feather: {file_path}")
            except ImportError:
                print("Warning: pyarrow not installed. Install with: pip install pyarrow")
                return False

        else:
            print(f"Warning: Unsupported format '{format}'. Defaulting to CSV.")
            df.to_csv(file_path + '.csv', index=False)
            print(f"✓ Data exported to CSV: {file_path}.csv")

        return True

    except Exception as e:
        print(f"Error: Failed to export data: {str(e)}")
        return False


def get_hierarchical_combinations(
    df: pd.DataFrame,
    levels: List[str]
) -> pd.DataFrame:
    """
    Get hierarchical administrative combinations.

    Helper function to extract unique hierarchical combinations of administrative
    levels from a dataframe. This ensures proper counting of admin units as
    combinations rather than isolated values.

    Parameters
    ----------
    df : pd.DataFrame
        A dataframe containing administrative level columns
    levels : list of str
        Column names representing hierarchical admin levels

    Returns
    -------
    pd.DataFrame
        A dataframe with unique combinations of the specified levels,
        excluding rows with any NA values
    """
    if not levels:
        return pd.DataFrame()

    # Filter to only the specified levels that exist in the dataframe
    existing_levels = [l for l in levels if l in df.columns]
    if not existing_levels:
        return pd.DataFrame()

    # Remove rows with any NA values and get unique combinations
    df_subset = df[existing_levels].copy()
    df_clean = df_subset.dropna()
    return df_clean.drop_duplicates()


def calculate_match_stats(
    data: pd.DataFrame,
    lookup_data: pd.DataFrame,
    level0: Optional[str] = None,
    level1: Optional[str] = None,
    level2: Optional[str] = None,
    level3: Optional[str] = None,
    level4: Optional[str] = None,
    use_rich: bool = True
) -> None:
    """
    Calculate and report geo-naming match statistics.

    Compares entries in a dataset against a lookup across specified admin levels
    and reports match statistics to the console.

    Parameters
    ----------
    data : pd.DataFrame
        A data frame containing the target data to be matched.
    lookup_data : pd.DataFrame
        A data frame serving as the reference for matching.
    level0 : str, optional
        Column name (country) present in both data and lookup_data.
    level1 : str, optional
        Column name (province/state/region) present in both datasets.
    level2 : str, optional
        Column name (district) present in both datasets.
    level3 : str, optional
        Column name (subdistrict) present in both datasets.
    level4 : str, optional
        Column name (settlement) present in both datasets.
    use_rich : bool, default True
        Use Rich library for beautiful output if available.
    """
    # Normalize case - work on copies to avoid modifying the original dataframes
    data = data.copy()
    lookup_data = lookup_data.copy()
    levels_vec = [l for l in [level0, level1, level2, level3, level4] if l is not None]

    if levels_vec:
        for lv in levels_vec:
            if lv in data.columns:
                data[lv] = data[lv].astype(str).str.lower()
            if lv in lookup_data.columns:
                lookup_data[lv] = lookup_data[lv].astype(str).str.lower()

    def compose_fields(*args):
        return [f for f in args if f is not None]

    def build_keys(df, fields):
        if not fields:
            return []
        combos = get_hierarchical_combinations(df, fields)
        if len(combos) == 0:
            return []
        if len(fields) == 1:
            return combos[fields[0]].unique().tolist()
        return (combos[fields].apply(lambda x: '_'.join(x.astype(str)), axis=1)
                .unique().tolist())

    def paint_matches(matches, total):
        num_str = f"{matches:,}"
        if matches < total:
            return f"\033[91m{num_str}\033[0m"  # Red color for mismatches
        return num_str

    results = {}

    def process_level(level_key, level_num, fields, label):
        data_keys = build_keys(data, fields)
        lookup_keys = build_keys(lookup_data, fields)
        matches = len(set(data_keys) & set(lookup_keys))
        results[level_key] = {
            'label': label if label else level_key,
            'level_num': level_num,
            'matches': matches,
            'total_data': len(data_keys),
            'total_lookup': len(lookup_keys)
        }

    # Compute per-level
    if level0:
        process_level("level0", 0, compose_fields(level0), level0)
    if level1:
        f1 = compose_fields(level0, level1) if level0 else compose_fields(level1)
        process_level("level1", 1, f1, level1)
    if level2:
        process_level("level2", 2, compose_fields(level0, level1, level2), level2)
    if level3:
        process_level("level3", 3, compose_fields(level0, level1, level2, level3), level3)
    if level4:
        process_level("level4", 4, compose_fields(level0, level1, level2, level3, level4), level4)

    # Check completeness
    ordered_keys = ["level0", "level1", "level2", "level3", "level4"]
    rows = [results[k] for k in ordered_keys if k in results]

    if rows:
        target_complete = all(r['matches'] == r['total_data'] for r in rows)
        lookup_complete = all(r['matches'] == r['total_lookup'] for r in rows)

    # Display results using Rich if available and requested
    if use_rich and RICH_AVAILABLE and console:
        _display_match_stats_rich(rows, target_complete, lookup_complete, levels_vec, data, lookup_data)
    else:
        _display_match_stats_plain(rows, target_complete, lookup_complete, levels_vec, data, lookup_data)


def _display_match_stats_rich(rows, target_complete, lookup_complete, levels_vec, data, lookup_data):
    """Display match statistics using Rich library for beautiful output."""
    # Create main panel title
    title = Text("ℹ Match Summary", style="bold")

    # Status message based on completeness
    if target_complete and lookup_complete:
        status_msg = Text("✓ Hierarchies are aligned across data and lookup", style="success")
    elif target_complete and not lookup_complete:
        status_msg = Text("ℹ Lookup has extra names not in data", style="info")
    elif not target_complete and lookup_complete:
        status_msg = Text("ℹ Data has names not in lookup", style="info")
    else:
        status_msg = Text("⚠ Both sides have unmatched names", style="warning")

    # Create table for match statistics with caption at bottom
    table = Table(
        box=box.ROUNDED,
        show_header=True,
        header_style="primary",
        title_style="bold",
        caption=status_msg,
        caption_justify="left",
        caption_style="",
    )

    # Add columns with original naming
    table.add_column("Level", style="highlight", no_wrap=True)
    table.add_column("Matched", justify="center", style="primary")
    table.add_column("Target Data N", justify="center")
    table.add_column("Lookup Data N", justify="center")

    # Add rows
    for r in rows:
        # Determine match quality color
        match_pct = (r['matches'] / max(r['total_data'], 1)) * 100
        if match_pct == 100:
            match_style = "success"
        elif match_pct >= 75:
            match_style = "info"
        elif match_pct >= 50:
            match_style = "warning"
        else:
            match_style = "error"

        table.add_row(
            f"{r['label']} (level{r['level_num']})",
            Text(str(r['matches']), style=match_style),
            str(r['total_data']),
            str(r['total_lookup'])
        )

    # Check for missing names
    missing_panel = None
    if levels_vec:
        miss_data = {lv: 0 for lv in levels_vec}
        miss_lookup = {lv: 0 for lv in levels_vec}

        for lv in levels_vec:
            if lv in data.columns:
                miss_data[lv] = ((data[lv].isna()) | (data[lv] == "")).sum()
            if lv in lookup_data.columns:
                miss_lookup[lv] = ((lookup_data[lv].isna()) | (lookup_data[lv] == "")).sum()

        any_missing = any(miss_data[lv] > 0 or miss_lookup[lv] > 0 for lv in levels_vec)

        if any_missing:
            missing_text = Text()
            for lv in levels_vec:
                msgs = []
                if miss_data[lv] > 0:
                    msgs.append(f"target={miss_data[lv]}")
                if miss_lookup[lv] > 0:
                    msgs.append(f"lookup={miss_lookup[lv]}")
                if msgs:
                    missing_text.append(f"\n• {lv}: ", style="muted")
                    missing_text.append(f"{', '.join(msgs)}", style="warning")

            missing_panel = Panel(
                missing_text,
                title="⚠ Missing Values Detected",
                title_align="left",
                border_style="warning",
                box=box.ROUNDED,
            )

    # Display everything - left aligned
    console.print()

    # Print title without panel
    console.print(title)
    console.print()

    # Print table directly without outer panel
    console.print(table)

    if missing_panel:
        console.print(missing_panel)
    console.print()

def _display_match_stats_plain(rows, target_complete, lookup_complete, levels_vec, data, lookup_data):
    """Display match statistics in plain text format (fallback)."""
    # Display results
    print("\n" + "="*93)
    print("ℹ Match Summary")
    print("="*93)

    if target_complete and lookup_complete:
        print("✓ Hierarchies are aligned across data and lookup.")
    elif target_complete and not lookup_complete:
        print("ℹ Lookup has extra names not in data.")
    elif not target_complete and lookup_complete:
        print("ℹ Data has names not in lookup.")
    else:
        print("⚠ Both sides have unmatched names; see per-level lines below.")

    # Check for missing names
    if levels_vec:
        miss_data = {lv: 0 for lv in levels_vec}
        miss_lookup = {lv: 0 for lv in levels_vec}

        for lv in levels_vec:
            if lv in data.columns:
                miss_data[lv] = ((data[lv].isna()) | (data[lv] == "")).sum()
            if lv in lookup_data.columns:
                miss_lookup[lv] = ((lookup_data[lv].isna()) | (lookup_data[lv] == "")).sum()

        any_missing = any(miss_data[lv] > 0 or miss_lookup[lv] > 0 for lv in levels_vec)

        if any_missing:
            print("⚠ Missing names detected in supplied levels (not included in N).")
            for lv in levels_vec:
                msgs = []
                if miss_data[lv] > 0:
                    msgs.append(f"data = {miss_data[lv]}")
                if miss_lookup[lv] > 0:
                    msgs.append(f"lookup = {miss_lookup[lv]}")
                if msgs:
                    print(f"  - {lv}: {', '.join(msgs)}")

    # Display two-column summary with proper alignment
    col_width = 45
    separator = " | "
    total_width = col_width * 2 + len(separator)  # This equals 93

    print("\n" + "-" * total_width)

    # Headers
    left_header = "Target data as base N"
    right_header = "Lookup data as base N"
    print(f"{left_header:<{col_width}}{separator}{right_header:<{col_width}}")
    print("-" * total_width)

    for r in rows:
        # Format the match statistics
        left_stat = f"{r['matches']:,} out of {r['total_data']:,} matched"
        right_stat = f"{r['matches']:,} out of {r['total_lookup']:,} matched"

        # Build the full lines
        left = f"• {r['label']} (level{r['level_num']}): {left_stat}"
        right = f"• {r['label']} (level{r['level_num']}): {right_stat}"

        # Print with consistent column width
        print(f"{left:<{col_width}}{separator}{right:<{col_width}}")

    print("="*93 + "\n")


def format_choice(index: int, choice: str, width: int) -> str:
    """Format a single choice for display."""
    number_part = f"{index:3d}: "
    remaining_width = width - len(number_part)

    if len(choice) > remaining_width - 4:  # -4 for "... "
        choice_part = choice[:remaining_width - 4] + "... "
    else:
        choice_part = choice

    choice_part = choice_part.ljust(remaining_width)
    return number_part + choice_part


def format_choices(choices: List[str], num_columns: int, column_width: int = 45) -> List[str]:
    """Format all choices into columns."""
    num_choices = len(choices)
    rows_per_column = (num_choices + num_columns - 1) // num_columns

    formatted_choices = []
    for i in range(rows_per_column):
        row_parts = []
        for j in range(num_columns):
            index = j * rows_per_column + i
            if index < num_choices:
                row_parts.append(format_choice(index + 1, choices[index], column_width))
            else:
                row_parts.append(" " * column_width)
        formatted_choices.append("".join(row_parts))

    return formatted_choices


def display_custom_menu(
    title: str,
    main_header: str,
    choices_input: List[str],
    special_actions: Dict[str, str],
    prompt: str,
    use_rich: bool = True
) -> str:
    """
    Display a custom menu and capture user choice.

    An alternative to simple input, displays a menu with given options and
    special actions, capturing user selection through a custom prompt.
    """
    if use_rich and RICH_AVAILABLE and console:
        return _display_menu_rich(title, main_header, choices_input, special_actions, prompt)
    else:
        return _display_menu_plain(title, main_header, choices_input, special_actions, prompt)


def _display_menu_rich(title: str, main_header: str, choices_input: List[str],
                       special_actions: Dict[str, str], prompt: str) -> str:
    """Display menu using Rich library for beautiful CLI interface."""
    from rich.layout import Layout
    from rich.panel import Panel
    from rich.columns import Columns
    from rich.text import Text
    from rich.rule import Rule

    # Clear console and create header
    console.clear()

    # Get console width for full-width lines
    console_width = console.width

    # Create header with full-width line (with leading dashes like in the image)
    console.print()
    # Custom format: "─── Text ───..."
    header_text = f"─── {main_header} "
    padding_length = console_width - len(f"─── {main_header} ")
    if padding_length > 0:
        header_line = header_text + "─" * padding_length
    else:
        header_line = header_text
    console.print(Text(header_line, style="bold cyan"))
    console.print()

    # Create title with highlighted name and full-width line (with leading dashes)
    title_parts = title.split("'")
    if len(title_parts) >= 3:
        # Create title with separate styling for the highlighted part
        title_text = Text("─── ", style="bold white")
        title_text.append(title_parts[0], style="bold white")
        title_text.append(f"'{title_parts[1]}'", style="bold red")
        title_text.append(title_parts[2] + " ", style="bold white")

        # Calculate padding
        plain_title = f"─── {title_parts[0]}'{title_parts[1]}'{title_parts[2]} "
        padding_length = console_width - len(plain_title)
        if padding_length > 0:
            title_text.append("─" * padding_length, style="bold white")
    else:
        title_line = f"─── {title} "
        padding_length = console_width - len(title_line)
        if padding_length > 0:
            title_line += "─" * padding_length
        title_text = Text(title_line, style="bold white")

    console.print(title_text)
    console.print()

    # Format choices in columns
    num_choices = len(choices_input)
    num_columns = 2 if num_choices > 20 else 1

    # Create choice panels
    choice_items = []
    for i, choice in enumerate(choices_input, 1):
        choice_text = Text()
        choice_text.append(f"{i:3}: ", style="bold cyan")
        choice_text.append(choice, style="white")
        choice_items.append(choice_text)

    # Split into columns
    if num_columns == 2:
        mid = (len(choice_items) + 1) // 2
        col1 = choice_items[:mid]
        col2 = choice_items[mid:]

        # Create two columns
        for i in range(max(len(col1), len(col2))):
            row_text = Text()
            if i < len(col1):
                row_text.append(col1[i])
                row_text.append(" " * (45 - len(str(col1[i]))))
            else:
                row_text.append(" " * 45)

            if i < len(col2):
                row_text.append(col2[i])

            console.print(row_text)
    else:
        for item in choice_items:
            console.print(item)

    console.print()

    # Special actions
    for key, action in special_actions.items():
        action_text = Text()
        action_text.append(f" {key}: ", style="bold yellow")
        action_text.append(action, style="white")
        console.print(action_text)

    console.print()

    # Prompt with style
    prompt_text = Text(prompt, style="bold cyan")

    while True:
        console.print(prompt_text, end="")
        choice = console.input().lower()
        valid_choices = [str(i) for i in range(1, len(choices_input) + 1)]
        valid_choices.extend([k.lower() for k in special_actions.keys()])

        if choice in valid_choices:
            break
        console.print(Text("Invalid choice, please try again.", style="error"))

    return choice


def _display_menu_plain(title: str, main_header: str, choices_input: List[str],
                        special_actions: Dict[str, str], prompt: str) -> str:
    """Display menu in plain text format (fallback)."""
    print("\n" + "="*60)
    print(main_header)
    print("-"*60)
    print(title)
    print("-"*60)

    num_choices = len(choices_input)
    num_columns = 3 if num_choices > 50 else (2 if num_choices > 25 else 1)

    formatted_choices = format_choices(choices_input, num_columns, column_width=45)

    print()
    for line in formatted_choices:
        print(line)
    print()

    for key, action in special_actions.items():
        print(f"{key}: {action}")

    print()

    while True:
        choice = input(prompt).lower()
        valid_choices = [str(i) for i in range(1, len(choices_input) + 1)]
        valid_choices.extend([k.lower() for k in special_actions.keys()])

        if choice in valid_choices:
            break
        print("Invalid choice, please try again.")

    return choice


def calculate_string_distance(
    admins_to_clean: List[str],
    lookup_admins: List[str],
    method: str = "jw"
) -> pd.DataFrame:
    """
    Calculate string distances between admin names.

    Computes the string distances between administrative names to be cleaned
    and a set of lookup administrative names using the specified method.
    Returns the top N closest matches for each name.
    """
    # Create all combinations
    results = pd.DataFrame([(n, m) for n in admins_to_clean for m in lookup_admins],
                          columns=['name_to_match', 'matched_names'])
    results = results.drop_duplicates()

    # Calculate distances
    if method == "jw":
        results['distance'] = results.apply(
            lambda x: jaro_winkler(x['name_to_match'], x['matched_names']), axis=1
        )
    elif method == "lv":
        results['distance'] = results.apply(
            lambda x: levenshtein(x['name_to_match'], x['matched_names']), axis=1
        )
    else:
        # Default to levenshtein for other methods
        results['distance'] = results.apply(
            lambda x: levenshtein(x['name_to_match'], x['matched_names']), axis=1
        )

    # Sort and rank
    results = (results
        .sort_values(['name_to_match', 'distance'])
        .assign(match_rank=lambda x: x.groupby('name_to_match').cumcount() + 1)
        .assign(algorithm_name=method))

    # Reorder columns
    return results[['algorithm_name', 'name_to_match', 'matched_names', 'distance', 'match_rank']]


def handle_user_interaction(
    input_data: pd.DataFrame,
    levels: List[str],
    level: str,
    clear_console: bool = True,
    max_options: int = 200
) -> pd.DataFrame:
    """
    Interact with users for data cleaning choices.

    Presents an interactive CLI menu for users to make selections on
    data cleaning choices, particularly for administrative names.
    """
    import random

    # Set up prompts
    prompts = [
        "What'll it be?:",
        "Your next move?:",
        "How shall we proceed?:",
        "Pick your path:",
        "Let's make a choice!:",
        "Where to next?:"
    ]
    prompt_text = random.choice(prompts)

    # Filter out missing values
    input_data = input_data[~input_data['matched_names'].isna() & ~input_data['name_to_match'].isna()]

    unique_names = input_data['name_to_match'].unique()
    user_choices = []

    i = 0
    while i < len(unique_names):
        if clear_console:
            os.system('cls' if os.name == 'nt' else 'clear')

        # Get current name to clean
        name_to_clean = unique_names[i]
        replacement_names = (input_data[input_data['name_to_match'] == name_to_clean]
                           ['matched_names'].unique()[:max_options])
        replacement_names = [str(n).title() for n in replacement_names]

        # Get geographic context
        geo_info = input_data[input_data['name_to_match'] == name_to_clean].iloc[0]
        long_geo = geo_info.get('long_geo', '')

        # Determine level label
        level_idx = levels.index(level) if level in levels else -1
        level_label = f"level{level_idx}"

        # Create title
        main_header = f"{level.title()} {i + 1} of {len(unique_names)}"
        title = f"Which {level} name would you like to replace '{name_to_clean.upper()}'?"

        if level_idx > 0 and long_geo:
            geo_parts = long_geo.split('_')
            if len(geo_parts) > 0:
                title += f" within {geo_parts[0].title()}"

        # Special actions
        special_actions = {
            "B": "Go Back",
            "S": "Skip this one",
            "E": "Save and exit",
            "Q": "Exit without saving",
            "M": "Enter name manually"
        }

        # Display menu and get choice (use Rich if available)
        user_choice = display_custom_menu(
            title, main_header, replacement_names,
            special_actions, prompt=prompt_text,
            use_rich=RICH_AVAILABLE
        )

        # Handle user choices
        if user_choice == "b":  # Go Back
            if i > 0:
                i -= 1
                continue
            else:
                print("Warning: You can't go back further.")
        elif user_choice == "s":  # Skip
            print("Info: You are skipping this one...")
            i += 1
            continue
        elif user_choice == "e":  # Save and exit
            if user_choices:
                print("Success: Choices saved successfully. Exiting...")
            else:
                print("Warning: No choices to save.")
            break
        elif user_choice == "q":  # Exit without saving
            confirm = input("Are you sure you want to exit without saving? [y/n]: ").lower()
            if confirm == "y":
                print("Danger: You have exited without saving...")
                return None
            else:
                print("Info: Returning to menu...")
        elif user_choice == "m":  # Manual entry
            manual_name = input("Enter the name manually: ")
            if manual_name:
                user_choices.append({
                    'level': level_label,
                    'name_to_match': name_to_clean,
                    'replacement': manual_name.upper(),
                    'longname_to_match': f"{long_geo}_{name_to_clean}" if long_geo else name_to_clean,
                    'longname_corrected': f"{long_geo}_{manual_name.upper()}" if long_geo else manual_name.upper(),
                    'created_time': datetime.now()
                })
                print("Success: Manual name entered successfully.")
            else:
                print("Warning: No name entered. Returning to menu...")
            i += 1
        else:
            try:
                idx = int(user_choice) - 1
                replace_name = replacement_names[idx].upper()
                user_choices.append({
                    'level': level_label,
                    'name_to_match': name_to_clean,
                    'replacement': replace_name,
                    'longname_to_match': f"{long_geo}_{name_to_clean}" if long_geo else name_to_clean,
                    'longname_corrected': f"{long_geo}_{replace_name}" if long_geo else replace_name,
                    'created_time': datetime.now()
                })
            except:
                pass
            i += 1

    if clear_console:
        os.system('cls' if os.name == 'nt' else 'clear')

    if user_choices:
        df = pd.DataFrame(user_choices)
        # Drop duplicates keeping the most recent
        df = df.sort_values('created_time', ascending=False).drop_duplicates('longname_to_match', keep='first')
        print("Success: Your selections have been successfully saved. Exiting...")
        return df
    else:
        print("Warning: No selections were made to save. Exiting...")
        return pd.DataFrame()


def construct_geo_names(
    data: pd.DataFrame,
    level0: Optional[str],
    level1: Optional[str],
    level2: Optional[str],
    level3: Optional[str] = None,
    level4: Optional[str] = None
) -> pd.DataFrame:
    """
    Construct long geographic names.

    This function creates a composite geographic identifier by concatenating
    values from specified administrative level columns within a dataframe.
    """
    def build_long_geo(row):
        parts = []
        for level in [level0, level1, level2, level3, level4]:
            if level and level in row.index and pd.notna(row[level]):
                parts.append(str(row[level]))
        return '_'.join(parts) if parts else ''

    data.loc[:, 'long_geo'] = data.apply(build_long_geo, axis=1)
    return data


def apply_case_mapping(
    df: pd.DataFrame,
    case_mapping: Optional[Dict[str, pd.DataFrame]],
    levels: List[str]
) -> pd.DataFrame:
    """
    Apply case mapping to data frame.

    Internal helper function to apply original case from lookup data
    to the matched values in the target data frame.
    """
    if not case_mapping:
        return df

    for level in levels:
        if level and level in df.columns and level in case_mapping:
            mapping = case_mapping[level]
            # Create a dict for fast lookup
            case_dict = dict(zip(mapping['uppercase'], mapping['original']))
            df[level] = df[level].map(lambda x: case_dict.get(x, x))

    return df


def get_user_identity() -> str:
    """Get the user identity from various environment variables."""
    return getpass.getuser()


def export_unmatched_data(
    target_todo: pd.DataFrame,
    unmatched_export_path: str,
    level0: Optional[str],
    level1: Optional[str],
    level2: Optional[str],
    level3: Optional[str],
    level4: Optional[str]
) -> None:
    """Export unmatched administrative names."""
    if len(target_todo) == 0:
        print("Info: No unmatched values to export")
        return

    # Get source names
    if 'target_data' in target_todo.columns and len(target_todo) > 0:
        target_name = target_todo['target_data'].iloc[0]
    else:
        target_name = 'NA'

    if 'lookup_data' in target_todo.columns and len(target_todo) > 0:
        lookup_name = target_todo['lookup_data'].iloc[0]
    else:
        lookup_name = 'NA'

    # Build list of columns to keep
    cols_to_keep = []
    for level in [level0, level1, level2, level3, level4]:
        if level and level in target_todo.columns:
            cols_to_keep.append(level)

    # Identify the unmatched column (most granular level)
    unmatched_column = 'NA'
    for level in [level4, level3, level2, level1, level0]:
        if level and level in cols_to_keep:
            unmatched_column = level
            break

    # Create export dataframe
    if cols_to_keep:
        unmatched_df = target_todo[cols_to_keep].drop_duplicates()
    else:
        unmatched_df = pd.DataFrame()

    unmatched_df['unmatched_column'] = unmatched_column
    unmatched_df['target_data'] = target_name
    unmatched_df['lookup_data'] = lookup_name
    unmatched_df['created_time'] = datetime.now()
    unmatched_df['name_of_creator'] = get_user_identity()

    # Reorder columns
    col_order = ['unmatched_column'] + cols_to_keep + ['target_data', 'lookup_data', 'created_time', 'name_of_creator']
    unmatched_df = unmatched_df[col_order]

    # Use the new export_dataframe function for consistent export handling
    export_success = export_dataframe(unmatched_df, unmatched_export_path)
    if export_success:
        print(f"Info: Exported {len(unmatched_df)} unmatched rows for column '{unmatched_column}'")


def prep_geonames(
    target_df: pd.DataFrame,
    lookup_df: Optional[pd.DataFrame] = None,
    level0: Optional[str] = None,
    level1: Optional[str] = None,
    level2: Optional[str] = None,
    level3: Optional[str] = None,
    level4: Optional[str] = None,
    cache_path: Optional[str] = None,
    unmatched_export_path: Optional[str] = None,
    output_path: Optional[str] = None,
    output_format: Optional[str] = None,
    method: str = "jw",
    interactive: bool = True,
    max_options: int = 200,
    preserve_case: bool = False
) -> pd.DataFrame:
    """
    Interactive Admin Name Cleaning and Matching.

    This function streamlines the admin name cleaning process, leveraging both
    algorithmic approaches and interactive user decisions. It combines string
    distance algorithms for initial matching and offers user interactivity for
    final decision-making, which are then saved for future reference and sharing.

    Parameters
    ----------
    target_df : pd.DataFrame
        Data frame containing the admin names to clean.
    lookup_df : pd.DataFrame, optional
        Lookup data frame for verifying admin names.
    level0 : str, optional
        level0 col name (country) in both data and lookup_data.
    level1 : str, optional
        level1 col name (province) in both data and lookup_data.
    level2 : str, optional
        level2 col name (district) in both data and lookup_data.
    level3 : str, optional
        level3 col name (subdistrict) in both data and lookup_data.
    level4 : str, optional
        level4 col name (settlement) in both data and lookup_data.
    cache_path : str, optional
        Path where the cache data frame is saved after user modifications.
    unmatched_export_path : str, optional
        Path to save unmatched data after processing.
    output_path : str, optional
        Path to save the cleaned data. Format inferred from extension or output_format.
    output_format : str, optional
        Output format for the cleaned data. Options: 'csv', 'xlsx', 'rds', 'parquet',
        'pickle', 'json', 'feather'. If None, inferred from output_path extension.
    method : str, default "jw"
        String distance calculation method to be used.
    interactive : bool, default True
        If True, prompts the user for interactive matching decisions.
    max_options : int, default 200
        Maximum number of options to output for string distance matching.
    preserve_case : bool, default False
        If True, preserves the original case of admin names from the lookup data.

    Returns
    -------
    pd.DataFrame
        A data frame with cleaned administrative names.
    """
    # Store original names for later reference
    target_df_name = "target_df"
    lookup_df_name = "lookup_df" if lookup_df is not None else "internal_lookup"

    # Validation
    if level1 and not level0:
        raise ValueError("You cannot specify level1 without level0.")
    if level2 and (not level0 or not level1):
        raise ValueError("You cannot specify level2 without both level0 and level1.")
    if level3 and (not level0 or not level1 or not level2):
        raise ValueError("You cannot specify level3 without level0, level1, and level2.")
    if level4 and (not level0 or not level1 or not level2 or not level3):
        raise ValueError("You cannot specify level4 without level0, level1, level2, and level3.")

    # Check for required columns
    required_columns = [l for l in [level0, level1, level2, level3, level4] if l]

    if lookup_df is not None:
        missing_cols = set(required_columns) - set(lookup_df.columns)
        if missing_cols:
            raise ValueError(f"The following columns are missing in lookup_df: {', '.join(missing_cols)}")

    missing_cols = set(required_columns) - set(target_df.columns)
    if missing_cols:
        raise ValueError(f"The following columns are missing in target_df: {', '.join(missing_cols)}")

    # Validate method
    supported_methods = ["jw", "lv", "osa", "dl", "hamming", "lcs", "qgram", "cosine", "jaccard", "soundex"]
    if method not in supported_methods:
        raise ValueError(f"Unsupported method: {method}. Supported methods are: {', '.join(supported_methods)}")

    # Validate cache_path
    if cache_path and not os.path.exists(os.path.dirname(cache_path) or '.'):
        raise ValueError("The directory for cache_path does not exist.")

    # Validate lookup_df
    if lookup_df is not None and len(lookup_df) == 0:
        raise ValueError("The lookup_df is empty.")

    # Setup levels
    levels = [l for l in [level0, level1, level2, level3, level4] if l]

    # Store original case mapping if preserve_case is True
    lookup_case_mapping = None
    if preserve_case and lookup_df is not None:
        lookup_case_mapping = {}
        for level in levels:
            if level in lookup_df.columns:
                original_values = lookup_df[level]
                uppercase_values = original_values.str.upper()
                mapping_df = pd.DataFrame({
                    'uppercase': uppercase_values,
                    'original': original_values
                }).drop_duplicates()
                lookup_case_mapping[level] = mapping_df

    # Convert to uppercase for matching
    target_df = target_df.copy()
    for level in levels:
        if level in target_df.columns:
            # Handle None/NaN values properly
            target_df[level] = target_df[level].apply(lambda x: str(x).upper() if pd.notna(x) else x)

    if lookup_df is not None:
        lookup_df = lookup_df.copy()
        for level in levels:
            if level in lookup_df.columns:
                lookup_df[level] = lookup_df[level].astype(str).str.upper()

    # Handle cache
    saved_cache_df = pd.DataFrame()
    if cache_path and os.path.exists(cache_path):
        try:
            # Check file extension to determine format
            cache_ext = Path(cache_path).suffix.lower()
            if cache_ext in ['.xlsx', '.xls']:
                saved_cache_df = pd.read_excel(cache_path)
            elif cache_ext == '.csv':
                saved_cache_df = pd.read_csv(cache_path)
            else:
                # Default to pickle for .pkl or unknown extensions
                with open(cache_path, 'rb') as f:
                    saved_cache_df = pickle.load(f)
            print(f"Info: Loaded cache from {cache_path}")

            # Reconstruct longname_to_match if not present (it's not saved in cache)
            if 'longname_to_match' not in saved_cache_df.columns:
                saved_cache_df['longname_to_match'] = saved_cache_df.apply(
                    lambda row: row['name_to_match'] if row['level'] == 'level0' else
                               f"{row['level0_prepped']}_{row['name_to_match']}" if row['level'] == 'level1' and pd.notna(row.get('level0_prepped')) else
                               f"{row['level0_prepped']}_{row['level1_prepped']}_{row['name_to_match']}" if row['level'] == 'level2' and pd.notna(row.get('level0_prepped')) and pd.notna(row.get('level1_prepped')) else
                               f"{row['level0_prepped']}_{row['level1_prepped']}_{row['level2_prepped']}_{row['name_to_match']}" if row['level'] == 'level3' and pd.notna(row.get('level0_prepped')) and pd.notna(row.get('level1_prepped')) and pd.notna(row.get('level2_prepped')) else
                               f"{row['level0_prepped']}_{row['level1_prepped']}_{row['level2_prepped']}_{row['level3_prepped']}_{row['name_to_match']}" if row['level'] == 'level4' and pd.notna(row.get('level0_prepped')) and pd.notna(row.get('level1_prepped')) and pd.notna(row.get('level2_prepped')) and pd.notna(row.get('level3_prepped')) else
                               row['name_to_match'],  # fallback to just name_to_match
                    axis=1
                )
        except:
            print(f"Warning: Could not load cache from {cache_path}")
    elif cache_path and not os.path.exists(cache_path):
        print(f"Info: The specified cache file '{cache_path}' does not exist.")
        if interactive:
            user_input = input("Are you aware that the cache file is missing? Proceed to create a new one? (yes/no): ")
            if user_input.lower() not in ['yes', 'y']:
                print("Info: Exiting without creating a new cache file.")
                return None
            else:
                print("Info: Proceeding to create a new cache file...")
        else:
            print("Info: Non-interactive session detected; proceeding to create a new cache file.")

    # Apply cached corrections if available
    if len(saved_cache_df) > 0:
        # Apply corrections from cache
        for i, level in enumerate(levels):
            level_label = f"level{i}"
            cache_for_level = saved_cache_df[saved_cache_df['level'] == level_label]

            if len(cache_for_level) > 0:
                # Create mapping dictionary
                mapping = dict(zip(cache_for_level['name_to_match'],
                                 cache_for_level['replacement']))
                target_df[level] = target_df[level].map(lambda x: mapping.get(x, x))

    # Store original df
    orig_df = target_df.copy()

    # Filter for missing geolocations
    target_df_na = target_df[target_df[levels].isna().any(axis=1)]
    target_df = target_df.dropna(subset=levels)

    # Construct long geonames
    target_df = construct_geo_names(target_df, level0, level1, level2, level3, level4)
    if lookup_df is not None:
        lookup_df = construct_geo_names(lookup_df, level0, level1, level2, level3, level4)

        # Re-apply uppercase to lookup_df after construct_geo_names
        # This ensures matching works correctly after replacements
        for level in levels:
            if level in lookup_df.columns:
                lookup_df[level] = lookup_df[level].astype(str).str.upper()


    # Filter to matched/unmatched rows
    if lookup_df is not None:
        lookup_keys = set(lookup_df['long_geo'].unique())
        target_done = target_df[target_df['long_geo'].isin(lookup_keys)].copy()
        target_todo = target_df[~target_df['long_geo'].isin(lookup_keys)].copy()
    else:
        target_done = target_df
        target_todo = pd.DataFrame()

    # Calculate match stats
    if lookup_df is not None:
        # Use Rich output if available for better visuals
        calculate_match_stats(target_df, lookup_df, level0, level1, level2, level3, level4, use_rich=True)

    # Early return if all matched
    if len(target_todo) == 0:
        print("Success: All records matched; process completed. Exiting...")
        finalised_df = orig_df
        if preserve_case:
            finalised_df = apply_case_mapping(finalised_df, lookup_case_mapping, levels)

        # Export the cleaned data if output_path is specified
        if output_path:
            export_success = export_dataframe(finalised_df, output_path, output_format)
            if not export_success and interactive:
                user_input = input("Export failed. Do you want to continue anyway? [y/n]: ").lower()
                if user_input != 'y':
                    print("Exiting due to export failure.")
                    return None

        return finalised_df

    # Return if non-interactive
    if not interactive:
        print("Success: In non-interactive mode. Exiting after matching with cache...")

        # Export unmatched data
        if unmatched_export_path and len(target_todo) > 0:
            target_todo_copy = target_todo.copy()
            target_todo_copy['target_data'] = target_df_name
            target_todo_copy['lookup_data'] = lookup_df_name
            export_unmatched_data(target_todo_copy, unmatched_export_path, level0, level1, level2, level3, level4)

        if preserve_case:
            orig_df = apply_case_mapping(orig_df, lookup_case_mapping, levels)
        return orig_df

    print("Info: Partial match completed. There are still matches to be made.")
    user_input = input("Would you like to do interactive matching? (yes/no): ")

    if user_input.lower() not in ['yes', 'y']:
        print("Info: Exiting without interactive matching...")
        if preserve_case:
            orig_df = apply_case_mapping(orig_df, lookup_case_mapping, levels)
        return orig_df

    # Interactive string distance matching
    cleaned_dfs = []
    skip_to_end = False

    for level in levels:
        if skip_to_end:
            break

        level_idx = levels.index(level)

        # Handle hierarchical matching for non-base levels
        if level_idx > 0 and lookup_df is not None:
            grouping_level = levels[level_idx - 1]
            top_res_list = []

            for group in target_todo[grouping_level].unique():
                # Match group with lookup_df - uppercase the group for comparison
                # since lookup_df columns are uppercased but target_todo might have mixed case after replacements
                group_upper = str(group).upper()
                lookup_df_group = lookup_df[lookup_df[grouping_level] == group_upper]

                if len(lookup_df_group) == 0:
                    print(f"Warning: Group '{group}' in {grouping_level} not found in lookup data")
                    print(f"Danger: Skipping to end due to unmatched higher level")
                    skip_to_end = True
                    break
                # Use original group value for target_todo filtering
                unmatched_df_group = target_todo[
                    (target_todo[grouping_level] == group) &
                    (~target_todo[level].isin(lookup_df_group[level].unique()))
                ]

                if len(unmatched_df_group) == 0:
                    continue

                # Build long_geo for context
                long_geo_parts = []
                for prev_level in levels[:level_idx]:
                    if prev_level in unmatched_df_group.columns:
                        long_geo_parts.append(str(unmatched_df_group[prev_level].iloc[0]))
                long_geo_group = '_'.join(long_geo_parts) if long_geo_parts else group

                # Calculate string distances
                top_res = calculate_string_distance(
                    unmatched_df_group[level].unique().tolist(),
                    lookup_df_group[level].unique().tolist(),
                    method=method
                )
                # Keep all matches sorted by distance (not just the first one)
                # The user will see up to max_options in the menu
                top_res = (top_res
                    .drop(['algorithm_name'], axis=1)
                    .sort_values(['name_to_match', 'distance'])
                    .assign(long_geo=long_geo_group))

                top_res_list.append(top_res)

            if skip_to_end:
                print("Danger: Skipping to end due to unmatched higher level")
                break

            if top_res_list:
                top_res = pd.concat(top_res_list, ignore_index=True)
            else:
                continue
        elif lookup_df is not None:
            # Base level matching
            unmatched_df_group = target_todo[~target_todo[level].isin(lookup_df[level].unique())]

            if len(unmatched_df_group) == 0:
                continue

            top_res = calculate_string_distance(
                unmatched_df_group[level].unique().tolist(),
                lookup_df[level].unique().tolist(),
                method=method
            )
            # Keep all matches sorted by distance (not just the first one)
            # The user will see up to max_options in the menu
            top_res = (top_res
                .drop(['algorithm_name'], axis=1)
                .sort_values(['name_to_match', 'distance'])
                .assign(long_geo=lambda x: x['name_to_match']))
        else:
            continue

        # Handle user interaction
        if 'top_res' in locals() and len(top_res) > 0:
            print(f"Info: Handling user interaction for level: {level}")
            replacement_df = handle_user_interaction(
                top_res, levels, level, max_options=max_options
            )

            if replacement_df is not None and len(replacement_df) > 0:
                cleaned_dfs.append(replacement_df)
                print(f"Success: Replacements made for level: {level}")

                # Update target_todo with replacements
                mapping = dict(zip(replacement_df['name_to_match'],
                                 replacement_df['replacement']))
                target_todo.loc[:, level] = target_todo[level].map(lambda x: mapping.get(x, x))
            else:
                print(f"Warning: No replacements made for level: {level}")

            # Reconstruct geo names after updates
            target_todo = construct_geo_names(target_todo, level0, level1, level2, level3, level4)

            # Re-filter to remove items that are now matched after replacements
            if lookup_df is not None:
                lookup_keys = set(lookup_df['long_geo'].unique())
                newly_matched = target_todo[target_todo['long_geo'].isin(lookup_keys)]
                if len(newly_matched) > 0:
                    print(f"Info: {len(newly_matched)} items now match after replacements")
                    target_done = pd.concat([target_done, newly_matched], ignore_index=True)
                    target_todo = target_todo[~target_todo['long_geo'].isin(lookup_keys)].copy()

    # Save cache if changes were made
    if cleaned_dfs and any(len(df) > 0 for df in cleaned_dfs):
        cleaned_cache = pd.concat(cleaned_dfs, ignore_index=True)

        # Convert longname_corrected to level*_prepped columns (like R function does)
        if 'longname_corrected' in cleaned_cache.columns:
            # Split longname_corrected into level columns
            split_cols = cleaned_cache['longname_corrected'].str.split('_', expand=True, n=4)
            level_names = ['level0_prepped', 'level1_prepped', 'level2_prepped', 'level3_prepped', 'level4_prepped']

            for i, col_name in enumerate(level_names):
                if i < split_cols.shape[1]:
                    cleaned_cache[col_name] = split_cols[i]
                else:
                    cleaned_cache[col_name] = None

            # For level0, the replacement goes directly to level0_prepped
            cleaned_cache.loc[cleaned_cache['level'] == 'level0', 'level0_prepped'] = cleaned_cache.loc[cleaned_cache['level'] == 'level0', 'replacement']
            # For level1, the replacement goes to level1_prepped
            cleaned_cache.loc[cleaned_cache['level'] == 'level1', 'level1_prepped'] = cleaned_cache.loc[cleaned_cache['level'] == 'level1', 'replacement']
            # For level2, the replacement goes to level2_prepped
            cleaned_cache.loc[cleaned_cache['level'] == 'level2', 'level2_prepped'] = cleaned_cache.loc[cleaned_cache['level'] == 'level2', 'replacement']
            # For level3, the replacement goes to level3_prepped
            cleaned_cache.loc[cleaned_cache['level'] == 'level3', 'level3_prepped'] = cleaned_cache.loc[cleaned_cache['level'] == 'level3', 'replacement']
            # For level4, the replacement goes to level4_prepped
            cleaned_cache.loc[cleaned_cache['level'] == 'level4', 'level4_prepped'] = cleaned_cache.loc[cleaned_cache['level'] == 'level4', 'replacement']

            # Replace empty strings with None
            for col in level_names:
                cleaned_cache[col] = cleaned_cache[col].replace('', None)

        # Process for saving
        cleaned_cache['name_of_creator'] = get_user_identity()

        # Combine with existing cache
        if len(saved_cache_df) > 0:
            final_cache_df = pd.concat([saved_cache_df, cleaned_cache], ignore_index=True)
        else:
            final_cache_df = cleaned_cache

        # Reconstruct longname_to_match from level*_prepped columns (like R does)
        if not 'longname_to_match' in final_cache_df.columns or final_cache_df['longname_to_match'].isna().any():
            final_cache_df['longname_to_match'] = final_cache_df.apply(
                lambda row: row['name_to_match'] if row['level'] == 'level0' else
                           f"{row['level0_prepped']}_{row['name_to_match']}" if row['level'] == 'level1' else
                           f"{row['level0_prepped']}_{row['level1_prepped']}_{row['name_to_match']}" if row['level'] == 'level2' else
                           f"{row['level0_prepped']}_{row['level1_prepped']}_{row['level2_prepped']}_{row['name_to_match']}" if row['level'] == 'level3' else
                           f"{row['level0_prepped']}_{row['level1_prepped']}_{row['level2_prepped']}_{row['level3_prepped']}_{row['name_to_match']}" if row['level'] == 'level4' else
                           row.get('longname_to_match', ''),
                axis=1
            )

        # Drop duplicates using longname_to_match as the unique identifier
        final_cache_df = (final_cache_df
            .sort_values('created_time', ascending=False)
            .drop_duplicates('longname_to_match', keep='first'))

        # Select columns in the right order (matching R output)
        # NOTE: longname_to_match is NOT saved - it will be reconstructed when loading
        cache_columns = ['level', 'name_to_match', 'replacement',
                        'level0_prepped', 'level1_prepped', 'level2_prepped',
                        'level3_prepped', 'level4_prepped',
                        'created_time', 'name_of_creator']
        # Keep only columns that exist
        cache_columns = [col for col in cache_columns if col in final_cache_df.columns]
        final_cache_df = final_cache_df[cache_columns]

        # Save the cache
        handle_file_save(final_cache_df, default_save_path=cache_path)
    else:
        print("Warning: No cleanings were made. Cache will not be updated.")

    # Combine all data
    finalised_df = pd.concat([target_done, target_todo, target_df_na], ignore_index=True)
    if 'long_geo' in finalised_df.columns:
        finalised_df = finalised_df.drop('long_geo', axis=1)

    # Final stats
    if lookup_df is not None:
        calculate_match_stats(finalised_df, lookup_df, level0, level1, level2, level3, level4, use_rich=True)

    # Export final unmatched data
    if unmatched_export_path and len(target_todo) > 0 and lookup_df is not None:
        # Filter for still unmatched
        lookup_keys = set(lookup_df['long_geo'].unique())
        still_unmatched = target_todo[~target_todo['long_geo'].isin(lookup_keys)]

        if len(still_unmatched) > 0:
            still_unmatched_copy = still_unmatched.copy()
            still_unmatched_copy['target_data'] = target_df_name
            still_unmatched_copy['lookup_data'] = lookup_df_name
            export_unmatched_data(still_unmatched_copy, unmatched_export_path,
                                level0, level1, level2, level3, level4)

    # Apply case mapping if preserve_case is True
    if preserve_case:
        finalised_df = apply_case_mapping(finalised_df, lookup_case_mapping, levels)

    # Export the cleaned data if output_path is specified
    if output_path:
        export_success = export_dataframe(finalised_df, output_path, output_format)
        if not export_success and interactive:
            user_input = input("Export failed. Do you want to continue anyway? [y/n]: ").lower()
            if user_input != 'y':
                print("Exiting due to export failure.")
                return None

    return finalised_df


def impute_higher_admin(
    target_df: pd.DataFrame,
    target_lower_col: str,
    target_higher_col: str,
    lookup_df: pd.DataFrame,
    lookup_lower_col: str,
    lookup_higher_col: str
) -> pd.DataFrame:
    """
    Impute higher administrative level using a lookup table.

    This function imputes a higher-level administrative unit (e.g., adm1) based
    on a lower-level administrative unit (e.g., adm2) using a lookup table.

    Parameters
    ----------
    target_df : pd.DataFrame
        A dataframe containing the lower-level administrative unit column.
    target_lower_col : str
        Name of the lower-level admin column (e.g., adm2).
    target_higher_col : str
        Name of the higher-level admin column to be created.
    lookup_df : pd.DataFrame
        A dataframe containing the mapping of lower to higher-level units.
    lookup_lower_col : str
        Name of the lower-level column in the lookup table.
    lookup_higher_col : str
        Name of the higher-level column in the lookup table.

    Returns
    -------
    pd.DataFrame
        A dataframe with an additional higher-level column.
    """
    # Create mapping dictionary
    mapping = dict(zip(lookup_df[lookup_lower_col], lookup_df[lookup_higher_col]))

    # Apply mapping with default to original value
    target_df[target_higher_col] = target_df[target_lower_col].map(
        lambda x: mapping.get(x, x) if pd.notna(x) else x
    )

    return target_df
