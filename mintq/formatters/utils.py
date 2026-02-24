import json

import pandas as pd
from tabulate import tabulate


def format_df(
    df: pd.DataFrame,
    *,
    max_visible_rows: int = 20,
    max_cell_width: int = 200,
    tablefmt: str = "github",
    floatfmt: str = ".8g",
    add_bottom_ellipsis_row: bool = False,
) -> str:
    def truncate_cell(val: object) -> object:
        if pd.isna(val):
            return "[NULL]"  # Convert all nulls to string (pandas coerces None back to nan/NaT)
        if isinstance(val, str):
            # Collapse multi-line values into a single line to preserve table layout
            if "\n" in val or "\r" in val:
                # For JSON values, parse and re-dump compactly
                try:
                    parsed = json.loads(val)
                    val = json.dumps(parsed, separators=(",", ":"), ensure_ascii=False)
                except (json.JSONDecodeError, ValueError):
                    val = val.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")
            if len(val) > max_cell_width:
                half = max_cell_width // 2
                return val[:half] + "..." + val[-half:]
        return val

    # Apply truncation first to preserve numeric types (nulls stay as None for tabulate)
    display_df = df.map(truncate_cell)

    n = len(display_df)
    if n > max_visible_rows:
        first_n = (max_visible_rows + 1) // 2
        last_n = max_visible_rows - first_n
        head_df = display_df.head(first_n)
        tail_df = display_df.tail(last_n)
        ellipsis_row = pd.DataFrame([["..."] * len(df.columns)], columns=df.columns)
        display_df = pd.concat([head_df, ellipsis_row, tail_df], ignore_index=True)

    if add_bottom_ellipsis_row:
        ellipsis_row = pd.DataFrame([["..."] * len(df.columns)], columns=df.columns)
        display_df = pd.concat([display_df, ellipsis_row], ignore_index=True)

    # showindex=False hides the automatic row numbers
    return tabulate(
        display_df, headers="keys", tablefmt=tablefmt, showindex=False, missingval="[NULL]", floatfmt=floatfmt
    )
